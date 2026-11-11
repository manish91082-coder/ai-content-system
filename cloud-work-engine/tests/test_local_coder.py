import pathlib,sys,unittest,tempfile,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_coder import issue_ref,validate_patch,apply_patch_to_workspace
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

 def test_standalone_new_project_patch_applies_to_empty_git_workspace(self):
  patch_text=(
   "diff --git a/README.md b/README.md\n"
   "new file mode 100644\n"
   "--- /dev/null\n"
   "+++ b/README.md\n"
   "@@ -0,0 +1,2 @@\n"
   "+# API Rate Limiter\n"
   "+Local development guide\n"
  )
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)
   subprocess.run(["git","init","-q"],cwd=root,check=True)
   p=root/"task.patch";p.write_text(patch_text,encoding="utf-8")
   ok,result=apply_patch_to_workspace(p,root)
   self.assertTrue(ok,result)
   self.assertEqual(result["changed_files"],["README.md"])
   self.assertEqual((root/"README.md").read_text(encoding="utf-8"),"# API Rate Limiter\nLocal development guide\n")

if __name__=="__main__": unittest.main()
