from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[1]


class AboutMetadataTests(unittest.TestCase):
    def test_about_surface_and_appstream_urls(self):
        source = (ROOT / "src/linxira-package-center").read_text(encoding="utf-8")
        for text in ("APP_VERSION = \"0.2.2\"", "Linxira OS contributors", "MIT License", 'addMenu("Help")'):
            self.assertIn(text, source)

        component = ET.parse(ROOT / "data/org.linxira.PackageCenter.metainfo.xml").getroot()
        urls = {node.attrib["type"]: node.text for node in component.findall("url")}
        self.assertEqual(set(urls), {"homepage", "vcs-browser", "bugtracker", "help"})
        self.assertEqual(urls["vcs-browser"], "https://github.com/Linxira-OS/linxira-package-center")
        self.assertEqual(urls["bugtracker"], urls["vcs-browser"] + "/issues")


if __name__ == "__main__":
    unittest.main()
