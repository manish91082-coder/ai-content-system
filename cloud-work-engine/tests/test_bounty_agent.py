import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bounty_agent as agent

class BountyAgentTests(unittest.TestCase):
    def test_complete_cursor_pagination_and_deduplication(self):
        pages = [
            {"bounties": [{"_id": "a"}, {"_id": "b"}], "has_more": True, "next_cursor": "opaque-2"},
            {"bounties": [{"_id": "b"}, {"_id": "c"}], "has_more": False, "next_cursor": ""}
        ]
        with patch.object(agent, "request_json", side_effect=pages) as mocked:
            rows, meta = agent.page_bounties()
        self.assertEqual([x["_id"] for x in rows], ["a", "b", "c"])
        self.assertEqual(meta["pages"], 2)
        self.assertEqual(mocked.call_args_list[1].args[1]["cursor"], "opaque-2")

    def test_bounty_details_merge_without_losing_list_fields(self):
        with patch.object(agent, "request_json", return_value={
            "bounty": {"_id": "a", "verification": "must pass tests"},
            "attachments": [{"filename": "spec.pdf"}],
            "bid": None, "claim": None, "comments": []
        }):
            rows, meta = agent.enrich_bounties([{"_id": "a", "title": "Build API"}])
        self.assertEqual(rows[0]["title"], "Build API")
        self.assertEqual(rows[0]["verification"], "must pass tests")
        self.assertEqual(rows[0]["_agent_detail"]["attachments"][0]["filename"], "spec.pdf")

    def test_payout_and_budget_are_separate(self):
        result = agent.normalize({
            "_id": "x", "flow": "bid", "status": "open",
            "payout_cents": None, "budget_cents": 12000, "currency": "USD"
        })
        self.assertIsNone(result["payout_amount"])
        self.assertEqual(result["budget_amount"], "120")
        self.assertEqual(result["task_id"], "x")

    def test_test_bounty_is_marked_non_cash(self):
        result = agent.normalize({"_id": "t", "flow": "bid", "status": "open", "test": True})
        self.assertTrue(result["test_bounty"])
        self.assertFalse(result["writes_enabled"])

if __name__ == "__main__":
    unittest.main()
