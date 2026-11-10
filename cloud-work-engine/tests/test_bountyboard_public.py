import pathlib, sys, unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bountyboard_public as board

class BountyBoardTests(unittest.TestCase):
    def test_supported_api_envelopes(self):
        self.assertEqual(board.rows_from({"bounties":[{"id":"a"}]})[0]["id"], "a")
        self.assertEqual(board.rows_from({"data":{"items":[{"id":"b"}]}})[0]["id"], "b")

    def test_funded_field_and_90pct_net(self):
        row = {"_id":"x","title":"Agent coding task","description":"Build an API","status":"open","currency":"USD","reward":"100","agentsAllowed":True,"escrow":{"status":"funded"}}
        item = board.normalize(row)
        self.assertEqual(item["task_id"], "x")
        self.assertEqual(item["estimated_agent_payout_after_10pct_fee"], "90.00")
        self.assertEqual(board.classify(item)[0], "CANDIDATE_REQUIRES_DETAIL_REVIEW")

    def test_no_escrow_field_never_assumed_funded(self):
        item = board.normalize({"id":"y","title":"AI coding","description":"Build","status":"open","currency":"USD","reward":"50","agentsAllowed":True})
        self.assertEqual(item["funded_signal"], "UNKNOWN")
        self.assertEqual(board.classify(item)[0], "REVIEW_REQUIRED")

    def test_schoolwork_excluded(self):
        item = board.normalize({"id":"z","title":"Writing schoolwork","description":"Translate english language tasks","status":"open","currency":"USD","reward":"1","agentsAllowed":True,"funded":True})
        self.assertEqual(board.classify(item)[0], "EXCLUDED")

    def test_physical_presence_excluded(self):
        item = board.normalize({"id":"p","title":"Add 20 local places","description":"Walk around Prague and take your own photo","status":"open","currency":"CZK","reward":"2400","agentsAllowed":True,"funded":True})
        self.assertEqual(board.classify(item)[0], "EXCLUDED")

    def test_pagination_uses_cursor_even_when_short_page(self):
        pages = [
            {"bounties":[{"_id":"a"}],"has_more":True,"next_cursor":"page-2"},
            {"bounties":[{"_id":"b"}],"has_more":False,"next_cursor":None}
        ]
        with patch.object(board, "get_json", side_effect=pages) as mocked:
            rows, meta = board.scan()
        self.assertEqual([x["_id"] for x in rows],["a","b"])
        self.assertEqual(meta["pages"],2)
        self.assertIn("cursor=page-2",mocked.call_args_list[1].args[0])

if __name__ == "__main__":
    unittest.main()
