import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "product" / "admission-desk-lite.html"


class AppAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.external_scripts = []
        self.inline_script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "script":
            if attrs.get("src"):
                self.external_scripts.append(attrs["src"])
            else:
                self.inline_script = True


class ProductKitTests(unittest.TestCase):
    def test_html_parses_and_has_required_controls(self):
        content = APP.read_text(encoding="utf-8")
        parser = AppAudit()
        parser.feed(content)
        self.assertTrue(parser.inline_script)
        self.assertEqual(parser.external_scripts, [])
        for item in ["lead-form", "guardian", "phone", "course", "stage",
                     "next-date", "consent", "export-btn", "import-btn",
                     "lead-rows", "m-due"]:
            self.assertIn(item, parser.ids)

    def test_privacy_and_manual_send_boundaries_are_visible(self):
        content = APP.read_text(encoding="utf-8").lower()
        self.assertIn("local storage", content)
        self.assertIn("message अपने-आप send नहीं होता", content)
        self.assertIn("no analytics", content)
        self.assertIn("https://wa.me/", content)

    def test_templates_and_validation_docs_exist(self):
        self.assertTrue((ROOT / "product" / "MESSAGE_TEMPLATES.md").exists())
        self.assertTrue((ROOT / "MISSION" / "PHASE_6_MARKET_VALIDATION.md").exists())


if __name__ == "__main__":
    unittest.main()
