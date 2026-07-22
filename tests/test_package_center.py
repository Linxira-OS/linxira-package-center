from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


ROOT = Path(__file__).parents[1]
CLIENT = ROOT / "src/linxira-package-center"
DESKTOP = ROOT / "data/org.linxira.PackageCenter.desktop"
VERSION = ROOT / "VERSION"

loader = importlib.machinery.SourceFileLoader("linxira_package_center", str(CLIENT))
spec = importlib.util.spec_from_loader(loader.name, loader)
package_center = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = package_center
loader.exec_module(package_center)


def application(identifier, category, *, default=False, order=0, review="reviewed", status="available",
                channel="default", provider="pacman", source="arch", license_class="open-source"):
    return {
        "id": identifier,
        "kind": "application",
        "name": {"en": identifier.title()},
        "description": {"en": f"{identifier} description"},
        "primaryCategory": category,
        "provider": provider,
        "source": source,
        "artifact": {"type": "package", "ids": [identifier]},
        "license": {
            "classification": license_class,
            "spdx": "LicenseRef-Test" if license_class != "open-source" else "MIT",
            "requiresAcceptance": license_class == "proprietary",
        },
        "review": {"status": review},
        "availability": {
            "status": status,
            "channel": channel,
            "reason": "Explicit third-party opt-in is required." if channel == "optional-review" else "",
        },
        "presentation": {"recommended": default, "defaultSelected": default, "order": order},
    }


def catalog_v3(*, compatible_roots=True) -> dict:
    categories = [
        {
            "id": "app-web", "kind": "category", "surface": "applications",
            "name": {"en": "Web", "zh_CN": "浏览器"}, "selection": {"mode": "exclusive"},
            "children": ["firefox", "chromium", "brave"], "order": 10,
        },
        {
            "id": "app-office", "kind": "category", "surface": "applications",
            "name": {"en": "Office"}, "selection": {"mode": "bounded", "maxSelected": 2},
            "children": ["writer", "sheets", "slides", "wps-office"], "order": 20,
        },
        {
            "id": "cap-runtime", "kind": "category", "surface": "components",
            "name": {"en": "Runtime"}, "selection": {"mode": "multi"},
            "children": ["component-python"], "order": 30,
        },
    ]
    applications = [
        application("firefox", "app-web", default=True, order=20),
        application("chromium", "app-web", order=10),
        application("brave", "app-web", order=30, review="source-review-pending",
                    status="review-channel", channel="optional-review", provider="aur", source="aur",
                    license_class="mixed"),
        application("writer", "app-office", default=True, order=10),
        application("sheets", "app-office", default=True, order=20),
        application("slides", "app-office", default=True, order=30),
        application("wps-office", "app-office", order=40, review="legal-review-pending",
                    status="review-channel", channel="optional-review", provider="aur", source="aur",
                    license_class="proprietary"),
        application("pending", "app-office", review="vm-test-pending"),
    ]
    bundles = []
    if compatible_roots:
        for category in categories[:2]:
            bundles.append({
                "id": category["id"], "selection": category["selection"],
                "children": {"required": [], "recommended": [], "optional": category["children"]},
            })
    return {
        "catalogVersion": 3,
        "release": "2026.07",
        "sources": [
            {"id": "arch", "userOptInRequired": False},
            {"id": "aur", "userOptInRequired": True},
        ],
        "categories": categories,
        "applications": applications,
        "components": [{"id": "component-python"}],
        "bundles": bundles,
        "operations": [],
    }


def catalog_v2() -> dict:
    return {
        "catalogVersion": 2,
        "categories": [{"id": "dev", "name": {"en": "Development"}}],
        "applications": [{
            "id": "kate", "name": {"en": "Kate"}, "description": {"en": "Editor"},
            "categories": ["dev"], "source": "arch", "installer": True,
            "review": {"status": "reviewed"}, "presentation": {"defaultSelected": False},
        }],
    }


class PackageCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_application = QApplication.instance() or QApplication([])

    def write_catalog(self, document):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "catalog.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        self.addCleanup(temporary.cleanup)
        return path

    def test_source_version_and_v3_default_are_declared(self) -> None:
        self.assertEqual(VERSION.read_text(encoding="utf-8"), "0.2.1\n")
        self.assertEqual(package_center.DEFAULT_CATALOG_PATH, "/usr/share/linxira/catalog/catalog-v3.json")
        self.assertEqual(package_center.DEFAULT_COMPONENTS_CLI, "/usr/bin/linxira-components")
        self.assertEqual(package_center.DEFAULT_PKEXEC, "/usr/bin/pkexec")

    def test_v3_builds_application_tree_from_surface_categories_and_children(self) -> None:
        categories = package_center.load_catalog(self.write_catalog(catalog_v3()), {"firefox"})
        projected = {category.id: [app.id for app in category.applications] for category in categories}
        self.assertEqual(projected["app-web"], ["chromium", "firefox", "brave"])
        self.assertEqual(projected["app-office"], ["writer", "sheets", "slides", "wps-office"])
        self.assertNotIn("cap-runtime", projected)
        self.assertNotIn("pending", projected["app-office"])
        firefox = next(app for app in categories[0].applications if app.id == "firefox")
        self.assertTrue(firefox.installed)

    def test_optional_review_channel_is_third_party_opt_in_and_not_selectable(self) -> None:
        categories = package_center.load_catalog(self.write_catalog(catalog_v3()))
        applications = {app.id: app for category in categories for app in category.applications}
        wps = applications["wps-office"]
        self.assertEqual(wps.channel, "optional-review")
        self.assertEqual(wps.provider, "aur")
        self.assertTrue(wps.user_opt_in_required)
        self.assertIn("需要接受许可", wps.license)
        self.assertTrue(wps.requires_acceptance)
        self.assertFalse(wps.selectable)

    def test_v2_remains_supported_without_v3_fields(self) -> None:
        categories = package_center.load_catalog(self.write_catalog(catalog_v2()))
        self.assertEqual(categories[0].id, "dev")
        self.assertEqual(categories[0].applications[0].id, "kate")
        self.assertEqual(categories[0].mode, "multi")

    def test_catalog_rejects_unsafe_application_ids(self) -> None:
        document = catalog_v3()
        document["applications"].append(application("unsafe/id", "app-web"))
        with self.assertRaisesRegex(package_center.CatalogError, "application ID"):
            package_center.load_catalog(self.write_catalog(document))

    def test_installed_state_supports_list_and_state_map(self) -> None:
        self.assertEqual(package_center._installed_ids({
            "installedApplications": ["firefox"],
            "applications": {"kate": {"state": "installed-managed"}, "vlc": {"state": "available"}},
        }), {"firefox", "kate"})

    def test_detects_installed_applications_from_pacman_package_state(self) -> None:
        catalog = self.write_catalog(catalog_v3())
        result = mock.Mock(returncode=0, stdout="firefox\nwriter\nunrelated\n", stderr="")
        with mock.patch.object(package_center.shutil, "which", return_value="/usr/bin/pacman"), \
             mock.patch.object(package_center.subprocess, "run", return_value=result) as run:
            installed = package_center.detect_installed_applications(catalog)
        self.assertEqual(installed, {"firefox", "writer"})
        self.assertEqual(run.call_args.args[0], ["/usr/bin/pacman", "-Qq"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_pacman_state_removes_stale_external_application_state(self) -> None:
        catalog = self.write_catalog(catalog_v3())
        state = catalog.parent / "state.json"
        state.write_text(json.dumps({"installedApplications": ["firefox"]}), encoding="utf-8")
        result = mock.Mock(returncode=0, stdout="writer\n", stderr="")
        with mock.patch.object(package_center.shutil, "which", return_value="/usr/bin/pacman"), \
             mock.patch.object(package_center.subprocess, "run", return_value=result):
            installed = package_center.detect_installed_applications(catalog, state)
        self.assertEqual(installed, {"writer"})

    def make_window(self):
        categories = package_center.load_catalog(self.write_catalog(catalog_v3()), {"firefox"})
        window = package_center.PackageCenterWindow(
            categories, package_center.ComponentsBackend(Path("catalog.json"), "linxira-components")
        )
        self.addCleanup(window.close)
        return window

    def test_tree_constraints_installed_lock_and_review_channel_filter(self) -> None:
        window = self.make_window()
        self.assertFalse(window.application_items["firefox"].flags() & Qt.ItemFlag.ItemIsUserCheckable)
        self.assertFalse(window.application_items["wps-office"].flags() & Qt.ItemFlag.ItemIsUserCheckable)
        self.assertEqual(window.application_items["slides"].checkState(0), Qt.CheckState.Unchecked)

        window.application_items["chromium"].setCheckState(0, Qt.CheckState.Checked)
        self.assertEqual(window.application_items["chromium"].checkState(0), Qt.CheckState.Unchecked)
        self.assertEqual(window.selected_application_ids(), ["sheets", "writer"])

        window.filter_box.setCurrentIndex(2)
        self.assertFalse(window.application_items["wps-office"].isHidden())
        self.assertTrue(window.application_items["writer"].isHidden())
        window.show_details(window.application_items["wps-office"], None)
        self.assertIn("当前 backend 未支持", window.detail_text.text())
        self.assertIn("用户 opt-in：需要", window.detail_text.text())

    def test_v3_selection_document_and_selection_cli_argument(self) -> None:
        catalog_path = self.write_catalog(catalog_v3())
        backend = package_center.ComponentsBackend(catalog_path, "linxira-components", "pkexec")
        calls = []
        selection = {}

        def fake_run(command, check, capture_output, text):
            calls.append(command)
            if command[1] == "plan":
                selection_path = Path(command[command.index("--selection") + 1])
                selection.update(json.loads(selection_path.read_text(encoding="utf-8")))
                output_dir = Path(command[command.index("--output-dir") + 1])
                (output_dir / "request-plan.json").write_text('{"digest":"plan"}', encoding="utf-8")
            elif command[1] == "confirm":
                output_dir = Path(command[command.index("--output-dir") + 1])
                (output_dir / "confirmation.json").write_text('{}', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "ok", "")

        with mock.patch.object(package_center.subprocess, "run", side_effect=fake_run):
            transaction_dir, plan = backend.create_plan(["writer", "sheets", "writer"])
            output = backend.confirm_and_apply(transaction_dir)

        self.assertEqual(plan, {"digest": "plan"})
        self.assertEqual(output, "ok")
        self.assertIn("--selection", calls[0])
        self.assertNotIn("--application", calls[0])
        self.assertEqual(selection["schemaVersion"], "org.linxira.component-selection.v1")
        self.assertEqual(selection["selectedLeafIds"], ["sheets", "writer"])
        self.assertEqual(selection["selectedBundleIds"], ["app-office"])
        self.assertEqual(selection["leaves"][0]["requestedBy"], ["app-office/sheets"])
        self.assertEqual(selection["leaves"][0]["provenance"], ["optional", "user"])
        self.assertEqual(selection["providerRequirements"], ["pacman"])
        self.assertEqual(selection["sourceRequirements"], ["arch"])
        self.assertEqual(selection["catalogSha256"], hashlib.sha256(catalog_path.read_bytes()).hexdigest())
        self.assertEqual(calls[2][:3], ["pkexec", "linxira-components", "apply"])
        self.assertEqual(calls[2][3:], ["--confirmation", str(transaction_dir / "confirmation.json")])

    def test_v3_without_category_root_bundle_fails_closed_before_backend(self) -> None:
        backend = package_center.ComponentsBackend(
            self.write_catalog(catalog_v3(compatible_roots=False)), "linxira-components"
        )
        with mock.patch.object(package_center.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "selection-v1.*bundle 根"):
                backend.create_plan(["firefox"])
        run.assert_not_called()

    def test_v2_backend_still_uses_application_argument(self) -> None:
        backend = package_center.ComponentsBackend(self.write_catalog(catalog_v2()), "linxira-components")
        calls = []

        def fake_run(command, check, capture_output, text):
            calls.append(command)
            output_dir = Path(command[command.index("--output-dir") + 1])
            (output_dir / "request-plan.json").write_text('{}', encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "ok", "")

        with mock.patch.object(package_center.subprocess, "run", side_effect=fake_run):
            transaction_dir, _ = backend.create_plan(["kate"])
        self.addCleanup(lambda: package_center.shutil.rmtree(transaction_dir, ignore_errors=True))
        self.assertIn("--application", calls[0])
        self.assertNotIn("--selection", calls[0])

    def test_client_has_no_direct_package_manager_path(self) -> None:
        source = CLIENT.read_text(encoding="utf-8")
        self.assertNotIn("subprocess.run([\"pacman\"", source)
        self.assertNotIn("kdialog", source)

    def test_desktop_entry_uses_canonical_executable(self) -> None:
        desktop = DESKTOP.read_text(encoding="utf-8")
        self.assertIn("Name=Linxira Package Center", desktop)
        self.assertIn("Exec=/usr/bin/linxira-package-center", desktop)


if __name__ == "__main__":
    unittest.main()
