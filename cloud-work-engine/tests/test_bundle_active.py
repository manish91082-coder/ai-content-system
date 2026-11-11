import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bundle_active import export_bundle
class Tests(unittest.TestCase):
 def test_only_active_and_attachment_free(self):
  r=export_bundle({"active_work":[{"task_id":"1","status":"claimed","claim_status":"active","description":"code"},{"task_id":"2","status":"open","description":"x"},{"task_id":"3","status":"claimed","claim_status":"active","description":"file","attachments":[{"name":"a"}]},{"task_id":"4","status":"claimed","claim_status":"active","description":"test","test_bounty":True}]})
  self.assertEqual([x["task_id"] for x in r["tasks"]],["1"]);self.assertFalse(r["secrets_included"]);self.assertEqual(len(r["skipped"]),3)
 def test_unverified_and_empty_excluded(self):
  r=export_bundle({"active_work":[{"task_id":"a","status":"claimed","claim_status":"active","description":"x","detail_error":"bad"},{"task_id":"b","status":"claimed","claim_status":"active","description":""}]})
  self.assertEqual(r["tasks"],[])
if __name__=="__main__": unittest.main()
