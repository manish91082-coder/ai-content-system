import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from draft_executor import select_active_work, local_qa

class DraftExecutorTests(unittest.TestCase):
    def test_only_hired_active_paid_work_selected(self):
        rows = [
            {"task_id":"a","status":"claimed","claim_status":"active","description":"Do a useful task","test_bounty":False},
            {"task_id":"b","status":"open","claim_status":None,"description":"Not hired"},
            {"task_id":"c","status":"claimed","claim_status":"active","description":"test","test_bounty":True}
        ]
        selected, skipped = select_active_work(rows)
        self.assertEqual([x["task_id"] for x in selected], ["a"])
        self.assertEqual(len(skipped), 2)

    def test_attachments_are_not_silently_ignored(self):
        row={"task_id":"a","status":"claimed","claim_status":"active","description":"Do task","attachments":[{"filename":"input.pdf"}]}
        selected, skipped=select_active_work([row])
        self.assertEqual(selected, [])
        self.assertEqual(skipped[0]["reason"], "attachments_require_safe_ingestion")

    def test_local_qa_flags_short_output(self):
        result=local_qa("Too short", {"title":"Example"})
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["checks"]["minimum_substance"])

if __name__ == "__main__":
    unittest.main()
