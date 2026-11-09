import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "product" / "landing.html"
DEMO = ROOT / "product" / "demo.html"


class PageAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external_scripts = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.external_scripts.append(attrs["src"])
        if "id" in attrs:
            self.ids.add(attrs["id"])


class Phase7Tests(unittest.TestCase):
    def test_landing_page_is_static_truthful_and_links_to_assets(self):
        content = LANDING.read_text(encoding="utf-8")
        parser = PageAudit()
        parser.feed(content)
        self.assertEqual(parser.external_scripts, [])
        self.assertIn('href="demo.html"', content)
        self.assertIn('href="admission-desk-lite.html"', content)
        self.assertIn("not validated", content.lower())
        self.assertIn("No checkout", content)

    def test_demo_has_fictional_data_and_interactive_controls(self):
        content = DEMO.read_text(encoding="utf-8")
        parser = PageAudit()
        parser.feed(content)
        self.assertEqual(parser.external_scripts, [])
        for item in ["search", "filter", "rows", "total", "active", "demo", "due"]:
            self.assertIn(item, parser.ids)
        self.assertIn("fictional", content.lower())
        self.assertIn("addEventListener", content)

    def test_demo_does_not_transmit_data_or_load_remote_assets(self):
        content = DEMO.read_text(encoding="utf-8").lower()
        self.assertNotIn("fetch(", content)
        self.assertNotIn("xmlhttprequest", content)
        self.assertNotIn("<iframe", content)
        self.assertNotIn("<img", content)


if (typeof module !== "undefined") module.exports = {};
if __name__ == "__main__":
    unittest.main()
