# Delivery and Acceptance Checklist

## Before work
- [ ] Scope limited to one named workflow.
- [ ] Expected behavior and failure behavior documented.
- [ ] Repository access is least-privilege.
- [ ] Logs and sample data are sanitized.
- [ ] No secrets received in chat or committed files.
- [ ] Production changes and external actions are excluded unless separately approved.

## During work
- [ ] Root cause tied to source/log evidence.
- [ ] Change isolated on a branch.
- [ ] Regression test added for the reported defect.
- [ ] Failure behavior tested.
- [ ] Publishing, messaging, payments and data mutations remain fail-closed.
- [ ] Provider/model IDs checked against current official documentation.
- [ ] No unsupported claims or fabricated data added.

## Before handover
- [ ] Python compilation succeeds where applicable.
- [ ] Unit tests pass.
- [ ] Integration tests run only with customer-authorized test credentials.
- [ ] No live production publishing or customer messaging occurred.
- [ ] Change summary includes commit SHA and changed paths.
- [ ] Limitations and unverified items are explicit.
- [ ] Rollback instructions provided.
- [ ] Customer accepts the deliverable in writing.

## Evidence bundle
- Repository branch or pull request.
- Test workflow URL and result.
- Root-cause summary.
- Handover runbook.
- Explicit list of what was not tested.
