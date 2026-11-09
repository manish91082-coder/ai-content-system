import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "product" / "interview-scorecard.html"
DOC = ROOT / "MISSION" / "PHASE_7B_UJJAIN_PILOT_CANDIDATES.md"


class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.remote_scripts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "script" and attrs.get("src"):
            self.remote_scripts.append(attrs["src"])


class Phase7BTests(unittest.TestCase):
    def test_scorecard_controls_and_privacy_boundaries(self):
        content = PAGE.read_text(encoding="utf-8")
        parser = Audit()
        parser.feed(content)
        self.assertEqual(parser.remote_scripts, [])
        for required in ["permission", "code", "q1", "q12", "pain", "price", "save", "export", "erase"]:
            self.assertIn(required, parser.ids)
        self.assertIn("localStorage", content)
        self.assertIn("CSV", content)
        self.assertIn("no data network", content)

    def test_no_network_submission_or_remote_dependencies(self):
        content = PAGE.read_text(encoding="utf-8").lower()
        for forbidden in ["fetch(", "xmlhttprequest", "sendbeacon", "<iframe"]:
            self.assertNotIn(forbidden, content)

    def test_candidate_research_has_stop_rules_and_no_contact_claim(self):
        content = DOC.read_text(encoding="utf-8")
        self.assertIn("No contact has been made", content)
        self.assertIn("Stop rules", content)
        self.assertIn("permission", content.lower())


if __name__ == "__main__":
    unittest.main()
