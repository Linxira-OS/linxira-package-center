from pathlib import Path
import os
import shutil
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
CLIENT = ROOT / "src/linxira-package-center"
DESKTOP = ROOT / "data/org.linxira.PackageCenter.desktop"
VERSION = ROOT / "VERSION"


class PackageCenterTests(unittest.TestCase):
    def test_source_version_is_declared(self) -> None:
        self.assertEqual(VERSION.read_text(encoding="utf-8"), "0.1.0\n")

    def test_client_uses_catalog_bound_backend_transaction(self) -> None:
        script = CLIENT.read_text(encoding="utf-8")
        self.assertIn("catalog-v2.json", script)
        self.assertIn(".applications[]", script)
        self.assertIn('.review.status == "reviewed"', script)
        self.assertIn("plan_args+=(--application", script)
        self.assertIn('pkexec "$COMPONENTS_CLI" apply', script)
        self.assertNotIn("pkexec pacman", script)
        self.assertNotIn("linxira-config", script)

    def test_desktop_entry_uses_canonical_executable(self) -> None:
        desktop = DESKTOP.read_text(encoding="utf-8")
        self.assertIn("Name=Linxira Package Center", desktop)
        self.assertIn("Exec=/usr/bin/linxira-package-center", desktop)
        self.assertNotIn("linxira-software-center", desktop)

    def test_application_selection_reaches_plan_confirm_and_apply(self) -> None:
        if os.name == "nt":
            self.skipTest("end-to-end shell test runs under Linux, WSL, and CI")
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            catalog = root / "catalog.json"
            catalog.write_text("{}\n", encoding="utf-8")
            log = root / "components.log"
            components = fake_bin / "linxira-components"

            self._executable(
                fake_bin / "jq",
                "#!/usr/bin/env bash\n"
                "printf 'Media\\tharuna\\tHaruna\\tMedia player\\tfalse\\n'\n",
            )
            self._executable(
                fake_bin / "kdialog",
                "#!/usr/bin/env bash\n"
                "case \" $* \" in\n"
                "  *' --checklist '*) printf '\"haruna\"\\n' ;;\n"
                "esac\n",
            )
            self._executable(
                fake_bin / "pkexec",
                "#!/usr/bin/env bash\nexec \"$@\"\n",
            )
            self._executable(
                components,
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >>\"$LINXIRA_TEST_LOG\"\n"
                "command=$1\nshift\noutput_dir=''\n"
                "while [[ $# -gt 0 ]]; do\n"
                "  if [[ $1 == --output-dir ]]; then output_dir=$2; shift 2; else shift; fi\n"
                "done\n"
                "case $command in\n"
                "  plan) printf '{}\\n' >\"$output_dir/request-plan.json\" ;;\n"
                "  confirm) printf '{}\\n' >\"$output_dir/confirmation.json\" ;;\n"
                "  apply) printf 'installed\\n' ;;\n"
                "esac\n",
            )

            environment = os.environ.copy()
            bash = shutil.which("bash")
            self.assertIsNotNone(bash)
            fake_commands = [
                fake_bin / name
                for name in ("jq", "kdialog", "pkexec", "linxira-components")
            ]
            subprocess.run(
                [
                    bash,
                    "-c",
                    "chmod 755 "
                    + " ".join(shlex.quote(self._bash_path(path)) for path in fake_commands),
                ],
                check=True,
            )
            environment.update(
                {
                    "PATH": self._bash_path(fake_bin) + ":/usr/local/bin:/usr/bin:/bin",
                    "LINXIRA_CATALOG_PATH": self._bash_path(catalog),
                    "LINXIRA_COMPONENTS_CLI": self._bash_path(components),
                    "LINXIRA_TEST_LOG": self._bash_path(log),
                }
            )
            result = subprocess.run(
                [bash, self._bash_path(CLIENT)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            calls = log.read_text(encoding="utf-8") if log.exists() else ""

            self.assertEqual(
                result.returncode,
                0,
                "stdout:\n"
                + result.stdout
                + "\nstderr:\n"
                + result.stderr
                + "\ncalls:\n"
                + calls,
            )
            self.assertIn("plan --catalog", calls)
            self.assertIn("--application haruna", calls)
            self.assertIn("confirm --catalog", calls)
            self.assertIn("apply --confirmation", calls)

    @staticmethod
    def _executable(path: Path, contents: str) -> None:
        path.write_text(contents, encoding="utf-8", newline="\n")
        path.chmod(0o755)

    @staticmethod
    def _bash_path(path: Path) -> str:
        value = str(path.resolve()).replace("\\", "/")
        if os.name == "nt" and len(value) >= 3 and value[1:3] == ":/":
            return "/mnt/" + value[0].lower() + value[2:]
        return value


if __name__ == "__main__":
    unittest.main()
