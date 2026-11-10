import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jobbi_source_verifier import classify_source, parse_issue_url, is_cashworthy

class SourceVerifierTests(unittest.TestCase):
    def candidate(self):
        return {"source_board":"algora","reward_currency":"USD","reward_amount":"100","payment_state":"escrowed","claims_open":True,"lane":"agent","payout_grade":"B"}

    def issue(self, **changes):
        base={"state":"open","locked":False,"labels":[{"name":"💎 Bounty"}],"assignee":None,"assignees":[],"comments":2,"updated_at":"2026-11-10T00:00:00Z"}
        base.update(changes)
        return base

    def test_parse_github_issue(self):
        self.assertEqual(parse_issue_url("https://github.com/dozer/dozer/issues/1659"),("dozer/dozer",1659,"issues"))

    def test_non_github_url_is_not_falsely_verified(self):
        self.assertIsNone(parse_issue_url("https://bountybook.example/gigs/123"))

    def test_cashworthy_requires_grade_b_or_better(self):
        self.assertTrue(is_cashworthy(self.candidate()))
        row=self.candidate();row["payout_grade"]="C"
        self.assertFalse(is_cashworthy(row))

    def test_closed_or_locked_issue_excluded(self):
        self.assertEqual(classify_source(self.candidate(),self.issue(state="closed"),[]) [0],"EXCLUDED_SOURCE_CLOSED")
        self.assertEqual(classify_source(self.candidate(),self.issue(locked=True),[]) [0],"EXCLUDED_SOURCE_LOCKED")

    def test_withdrawn_bounty_maintainer_comment_excluded(self):
        comments=[{"body":"FYI, we stopped the bounty program. Payouts won't work."}]
        self.assertEqual(classify_source(self.candidate(),self.issue(),comments)[0],"EXCLUDED_PAYOUT_WITHDRAWN")

    def test_competing_attempt_or_pr_excluded(self):
        comments=[{"body":"/attempt #123\n\nI am working on the task."},{"body":"Submitted PR #987."}]
        self.assertEqual(classify_source(self.candidate(),self.issue(),comments)[0],"EXCLUDED_COMPETITION")

    def test_unassigned_unclaimed_issue_goes_to_operator_gate(self):
        decision,reason=classify_source(self.candidate(),self.issue(),[])
        self.assertEqual(decision,"CANDIDATE_NEEDS_OPERATOR_GATE")
        self.assertIn("operator",reason)

    def test_core_team_only_label_excluded(self):
        issue=self.issue(labels=[{"name":"👥 Core Team Only"}])
        self.assertEqual(classify_source(self.candidate(),issue,[])[0],"EXCLUDED_SOURCE_RESTRICTED")

if __name__ == "__main__":
    unittest.main()
