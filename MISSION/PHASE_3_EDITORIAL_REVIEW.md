# Secure Editorial Review Workflow — Phase 3

## What is implemented in this branch
- Generated content now persists the title, script, description, hashtags, thumbnail prompt, source references and evidence status needed for a real review.
- A deterministic SHA-256 fingerprint binds the review to the exact title, script, description, hashtags, thumbnail prompt and source references.
- `.github/workflows/editorial_review.yml` provides two distinct human steps:
  1. `prepare`: displays the review package in the GitHub Actions run summary and prints its fingerprint.
  2. `approve` or `reject`: re-fetches the record, recomputes the fingerprint, checks the authenticated GitHub actor against `EDITORIAL_APPROVER_LOGINS`, then calls a restricted database RPC.
- The database RPC only accepts the Supabase `service_role`, locks the content row, requires `pending_editorial_review`, checks the fingerprint, updates the editorial status and appends an audit event in one transaction.
- Audit events are protected against UPDATE and DELETE by a trigger. The audit table has RLS enabled and no anon/authenticated grants.
- The workflow does not publish, does not enable publishing, and does not treat a decision as revenue.

## Required one-time owner setup
1. Review `config/editorial_review_schema.sql` and apply it manually in the intended Supabase project's SQL Editor. This branch does not execute DDL against the live database.
2. Confirm the existing `content_items` table has UUID `id`, JSONB `metadata`, `status`, and `updated_at` columns. The SQL also normalizes valid legacy JSONB string values into objects and grants the service_role the minimum table access needed by this workflow.
3. In GitHub repository Settings → Secrets and variables → Actions:
   - Secret `SUPABASE_URL`
   - Secret `SUPABASE_SERVICE_KEY` (server-side service-role key only; never paste it into chat or commit it)
   - Variable `EDITORIAL_APPROVER_LOGINS` (comma-separated exact GitHub login allowlist; start with the repository owner only)
4. Ensure the Supabase Data API exposes the `public` schema and the `editorial_review_decide` function is reachable through RPC. Supabase changed default grants for new public tables/functions in late October 2026; do not assume default access exists. This SQL explicitly grants the function and audit-table access to service_role only. The review table itself is not queried from the client.
5. After schema and secrets are configured, run the workflow with action `prepare`, inspect the complete summary, then run `approve` or `reject` with the exact content ID and fingerprint.
6. Keep `PUBLISH_ENABLED` unset/false and scheduled runs in test mode. An approval is not authorization to publish.

## Security and limitations
- The service-role key is used only inside GitHub Actions; it is never placed in a browser, static page, log, or repository file.
- The allowlist checks the authenticated `github.actor`, not a free-form reviewer input.
- The SQL function is SECURITY INVOKER, requires the service_role request claim/database role, and is executable only by service_role.
- A changed package invalidates the fingerprint. A second decision on a non-pending row is rejected.
- Audit rows are append-only through the database trigger and restricted grants. A project owner with elevated database privileges can still alter schema/disable triggers; this is operational audit, not tamper-proof external notarization.
- This is not yet an end-to-end publishing queue. Approval changes the record to `editorially_approved`; publishing from a later run still requires durable private asset storage, queue retrieval, revocation handling and a separate release gate. Those are deliberately not bypassed here.
- Existing broad `FOR ALL USING (true)` policies in the legacy schema remain a production blocker and must be redesigned before exposing user-facing data. This migration does not pretend to repair every legacy policy.
- No schema has been deployed and no content has been approved by this change.

## Verification
Run:
```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -v
```


## CI evidence
- GitHub Actions run #29: https://github.com/manish91082-coder/ai-content-system/actions/runs/42652645914
- 30 tests passed; compile step covered `src`, `tests`, and `scripts`.
- Provider check remains degraded because Gemini key authentication fails; Groq metadata authentication/model listing succeeds.
