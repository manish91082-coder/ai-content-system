import unittest
from cloud_work_engine.scanner import unpack

class UnpackTests(unittest.TestCase):
    def test_documented_data_array_envelope(self):
        rows, cursor = unpack({"data":[{"id":"a"},{"id":"b"}]})
        self.assertEqual([r["id"] for r in rows], ["a","b"])
        self.assertIsNone(cursor)

    def test_root_meta_cursor(self):
        rows, cursor = unpack({"data":[{"id":"a"}],"meta":{"nextCursor":"p2"}})
        self.assertEqual(len(rows), 1)
        self.assertEqual(cursor, "p2")

    def test_data_object_envelope(self):
        rows, cursor = unpack({"data":{"jobs":[{"id":"x"}],"nextCursor":"p3"}})
        self.assertEqual(rows[0]["id"], "x")
        self.assertEqual(cursor, "p3")

    def test_legacy_jobs_array(self):
        rows, cursor = unpack({"jobs":[{"id":"legacy"}]})
        self.assertEqual(rows[0]["id"], "legacy")
        self.assertIsNone(cursor)

    def test_invalid_payload_is_safe(self):
        self.assertEqual(unpack(None), ([], None))
        self.assertEqual(unpack({"data":"unexpected"}), ([], None))

if __name__ == "__main__":
    unittest.main()
