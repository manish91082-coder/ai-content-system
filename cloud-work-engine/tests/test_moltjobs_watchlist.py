import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import moltjobs_watchlist as watch

def item(**changes):
    raw = {
        "status":"OPEN", "purpose":"MARKETPLACE", "participationMode":"BID",
        "budgetUsdc":"150", "tokenSymbol":"USDC", "funded":False,
        "escrowTxHash":None, "paymentStatus":None, "deadlineAt":"2026-11-12T08:00:00Z",
        "createdAt":"2026-11-09T08:00:00Z", "acceptanceCriteria":[{"id":"page"},{"id":"seo"}],
        "poster":{"displayName":"Poster"}, "inputData":{"generalDescription":"single page landing page"}
    }
    raw.update(changes)
    return {"platform":"MoltJobs","task_id":"m1","title":"Landing page","description":"Create responsive website","reward_amount":"150","reward_currency":"USDC","source_url":"https://moltjobs.io/open-jobs/m1","deadline":raw.get("deadlineAt"),"raw":raw}

class MoltJobsWatchlistTests(unittest.TestCase):
    def test_unfunded_fixed_budget_is_watch_only(self):
        result=watch.evaluate(item())
        self.assertEqual(result["decision"],"WATCH_ESCROW_PENDING")
        self.assertEqual(result["listed_budget"],"150")
        self.assertFalse(result["work_authorized"])
        self.assertFalse(result["bid_or_claim_sent"])

    def test_funded_escrow_still_needs_agent_assignment(self):
        result=watch.evaluate(item(funded=True,escrowTxHash="0xabc",paymentStatus="funded"))
        self.assertEqual(result["decision"],"FUNDED_REQUIRES_AGENT_ASSIGNMENT")
        self.assertEqual(result["income_recognized"],"0")

    def test_financial_advice_excluded(self):
        result=watch.evaluate(item(title="Global Sovereign Wealth Fund Investment Strategies"))
        self.assertEqual(result["decision"],"EXCLUDED_HIGH_RISK_DOMAIN")

    def test_low_value_excluded(self):
        result=watch.evaluate(item(budgetUsdc="5"))
        self.assertEqual(result["decision"],"EXCLUDED_LOW_VALUE_OR_NON_CASH")

    def test_referral_and_forum_reward_excluded(self):
        result=watch.evaluate(item(purpose="PLATFORM_REFERRAL",participationMode="AUTOMATIC_FORUM_REWARD"))
        self.assertEqual(result["decision"],"EXCLUDED_NON_MARKETPLACE")

    def test_funding_transition_detected_once(self):
        original_dir, original_file = watch.STATE_DIR, watch.STATE_FILE
        with tempfile.TemporaryDirectory() as tmp:
            watch.STATE_DIR=pathlib.Path(tmp)
            watch.STATE_FILE=pathlib.Path(tmp)/"state.json"
            try:
                task=watch.evaluate(item(funded=False))
                self.assertEqual(watch.detect_funding_transitions([task]),[])
                task=watch.evaluate(item(funded=True,escrowTxHash="0xabc"))
                self.assertEqual(len(watch.detect_funding_transitions([task])),1)
                self.assertEqual(watch.detect_funding_transitions([task]),[])
            finally:
                watch.STATE_DIR, watch.STATE_FILE = original_dir, original_file

if __name__ == "__main__":
    unittest.main()
