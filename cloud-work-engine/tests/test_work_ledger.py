import pathlib, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from work_ledger import reconcile

class WorkLedgerTests(unittest.TestCase):
    def test_acceptance_is_not_cash(self):
        result = reconcile([], {"e1": {"type": "submission.accepted", "subject_id": "b1"}})
        item = result["events"][0]
        self.assertEqual(item["lifecycle_state"], "ACCEPTED_NOT_YET_CASH")
        self.assertEqual(item["recognized_income"], 0)

    def test_work_completed_requires_independent_payout_reconciliation(self):
        result = reconcile([], {"e2": {"type": "work.completed", "subject_id": "b2"}})
        self.assertEqual(result["financial_ledger"]["settlement_events_unreconciled"], 1)
        self.assertEqual(result["financial_ledger"]["recognized_income"], 0)

    def test_claimed_event_matches_active_work_only_when_claim_active(self):
        active = [{"task_id":"b3","status":"claimed","claim_status":"active","claim_id":"c3"}]
        result = reconcile(active, {"e3": {"type":"bounty.claimed","subject_id":"b3"}})
        self.assertTrue(result["events"][0]["active_work_match"])
        self.assertIn("HIRED_ACTIVE_CLAIM_CONFIRMED", result["events"][0]["lifecycle_state"])

    def test_verification_failure_generates_revision_state(self):
        result = reconcile([], {"e4": {"type":"submission.verification_failed","subject_id":"b4"}})
        self.assertEqual(result["events"][0]["lifecycle_state"], "REVISION_REQUIRED")

if __name__ == "__main__":
    unittest.main()
