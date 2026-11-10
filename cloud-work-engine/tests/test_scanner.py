import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scanner", ROOT / "scanner.py")
SCANNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCANNER)

class AdapterTests(unittest.TestCase):
    def test_taskmarket_envelope(self):
        rows = SCANNER.extract_rows({"tasks":[{"id":"t1"}]},("tasks",))
        self.assertEqual(rows[0]["id"],"t1")

    def test_dealwork_data_envelope(self):
        rows = SCANNER.extract_rows({"data":{"jobs":[{"id":"d1"}]}},("data",))
        self.assertEqual(rows[0]["id"],"d1")

    def test_taskmarket_six_decimal_conversion(self):
        self.assertEqual(SCANNER.decimal_base_units("15000000"),"15")

    def test_taskmarket_missing_escrow_is_blocked(self):
        decision, reason = SCANNER.classify("Taskmarket",{"id":"x","status":"open"})
        self.assertEqual(decision,"BLOCKED")
        self.assertIn("escrow",reason)

    def test_taskmarket_escrow_reference_requires_review(self):
        decision, reason = SCANNER.classify("Taskmarket",{"id":"x","status":"open","escrowTxHash":"0xabc"})
        self.assertEqual(decision,"REVIEW_REQUIRED")
        self.assertIn("onchain",reason)

    def test_moltjobs_referral_excluded(self):
        decision, _ = SCANNER.classify("MoltJobs",{"purpose":"PLATFORM_REFERRAL","participationMode":"AUTOMATIC_FORUM_REWARD"})
        self.assertEqual(decision,"EXCLUDED")

    def test_dealwork_open_job_not_assumed_funded(self):
        decision, reason = SCANNER.classify("Dealwork",{"status":"posted","jobMode":"open","fixedPrice":"25.0000","posterFunded":False,"claimBlockedReason":"poster_unfunded"})
        self.assertEqual(decision,"BLOCKED")
        self.assertIn("funding",reason)

    def test_invalid_payload(self):
        self.assertEqual(SCANNER.extract_rows(None),[])

if __name__ == "__main__":
    unittest.main()
