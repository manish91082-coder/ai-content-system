import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from task_triage import classify

class TriageTests(unittest.TestCase):
    def test_fixed_claim_is_candidate_only_for_supported_category(self):
        row = {"status": "open", "flow": "claim", "payout_cents": 5000, "category": "software", "title": "Build a small Python tool"}
        self.assertEqual(classify(row)[0], "CANDIDATE_REQUIRES_ECONOMIC_QA")

    def test_bid_budget_never_becomes_fixed_payout(self):
        row = {"status": "open", "flow": "bid", "payout_cents": None, "budget_cents": 10000, "category": "writing", "title": "Write technical documentation"}
        result, reason = classify(row)
        self.assertEqual(result, "CANDIDATE_REQUIRES_ECONOMIC_QA")
        self.assertIn("pricing_signal", reason)

    def test_test_bounty_excluded(self):
        self.assertEqual(classify({"test_bounty": True})[0], "EXCLUDED")

    def test_sensitive_domain_excluded(self):
        row = {"status": "open", "flow": "claim", "payout_cents": 10000, "category": "medical", "title": "Write diagnosis"}
        self.assertEqual(classify(row)[0], "EXCLUDED")

    def test_purchase_dependency_reviewed(self):
        row = {"status": "open", "flow": "claim", "payout_cents": 10000, "category": "software", "title": "Install paid subscription"}
        self.assertEqual(classify(row)[0], "REVIEW_REQUIRED")

if __name__ == "__main__":
    unittest.main()
