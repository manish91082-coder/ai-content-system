import pathlib,sys,unittest,tempfile,subprocess,zipfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import local_coder
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


 def test_pact_standalone_work_generates_zip_and_not_submitted_review(self):
  patch_text=(
   "diff --git a/README.md b/README.md\n"
   "new file mode 100644\n"
   "--- /dev/null\n"
   "+++ b/README.md\n"
   "@@ -0,0 +1,2 @@\n"
   "+# API Rate Limiter\n"
   "+Token bucket implementation.\n"
   "diff --git a/src/limiter.py b/src/limiter.py\n"
   "new file mode 100644\n"
   "--- /dev/null\n"
   "+++ b/src/limiter.py\n"
   "@@ -0,0 +1,2 @@\n"
   "+class TokenBucket:\n"
   "+    pass\n"
   "diff --git a/tests/test_limiter.py b/tests/test_limiter.py\n"
   "new file mode 100644\n"
   "--- /dev/null\n"
   "+++ b/tests/test_limiter.py\n"
   "@@ -0,0 +1,4 @@\n"
   "+from src.limiter import TokenBucket\n"
   "+\n"
   "+def test_constructs():\n"
   "+    assert TokenBucket() is not None\n"
  )
  model_result={
   "summary":"Created a standalone rate-limiter project with implementation, test and README.",
   "patch":patch_text,
   "files_changed":["README.md","src/limiter.py","tests/test_limiter.py"],
   "risks":[],
   "tests_recommended":["Run pytest tests/test_limiter.py"],
   "confidence":0.95
  }
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)
   report=root/"report"
   worker=root/"worker"
   worker.mkdir()
   task={
    "source_platform":"PACT AI Market",
    "task_id":"pact-order-1",
    "order_id":"order-1",
    "order_stage":"ESCROWED",
    "title":"API rate limiter",
    "description":"Build a token-bucket rate limiter.",
    "verification":"Include implementation, a test and README.",
    "category":"software_or_research"
   }
   with patch.object(local_coder,"REPORT",report), patch.object(local_coder,"ask_model",return_value=model_result):
    result=local_coder.work(task,worker)
   self.assertEqual(result["status"],"patch_ready",result)
   self.assertEqual(set(result["changed_files"]),{"README.md","src/limiter.py","tests/test_limiter.py"})
   archive_path=pathlib.Path(result["project_zip"])
   self.assertTrue(archive_path.is_file())
   with zipfile.ZipFile(archive_path) as archive:
    self.assertEqual(set(archive.namelist()),{"README.md","src/limiter.py","tests/test_limiter.py"})
    self.assertIn("class TokenBucket",archive.read("src/limiter.py").decode("utf-8"))
   review=pathlib.Path(result["review_file"]).read_text(encoding="utf-8")
   self.assertIn("Submission: NOT SUBMITTED",review)
   self.assertIn("Tests: NOT RUN",review)
   self.assertEqual(result["submission"],"NOT_SUBMITTED")
   self.assertEqual(result["tests"],"NOT_RUN")

if __name__=="__main__": unittest.main()
