import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_coder import issue_ref,validate_patch
class LocalCoderTests(unittest.TestCase):
 def test_issue_url(self):
  self.assertEqual(issue_ref("issue https://github.com/o/r/issues/42"),("https://github.com/o/r.git","o/r",42))
 def test_missing_issue(self):
  self.assertIsNone(issue_ref("Write a tutorial about APIs"))
 def test_workflow_change_blocked(self):
  p="diff --git a/.github/workflows/deploy.yml b/.github/workflows/deploy.yml\n--- a/.github/workflows/deploy.yml\n+++ b/.github/workflows/deploy.yml\n"
  self.assertEqual(validate_patch(p),(False,"workflow_or_git_metadata_changes_blocked"))
 def test_path_traversal_blocked(self):
  p="diff --git a/../../etc/passwd b/../../etc/passwd\n--- a/../../etc/passwd\n+++ b/../../etc/passwd\n"
  self.assertEqual(validate_patch(p),(False,"unsafe_patch_path"))
 def test_source_patch_allowed(self):
  p="diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n@@ -1 +1 @@\n-x=1\n+x=2\n"
  self.assertEqual(validate_patch(p),(True,"ok"))
 def test_secret_paths_blocked(self):
  p="diff --git a/.env b/.env\n--- a/.env\n+++ b/.env\n"
  self.assertEqual(validate_patch(p),(False,"secret_file_change_blocked"))
if __name__=="__main__": unittest.main()
