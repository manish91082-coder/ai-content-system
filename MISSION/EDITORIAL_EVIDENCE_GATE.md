# Editorial Evidence Gate — Phase 2 Engineering

## Objective
Prevent the automated pipeline from treating a headline or trend signal as sufficient evidence for a factual news script. Preserve traceable source metadata and constrain generated scripts/descriptions to the supplied source excerpts.

## Implemented
- RSS topic records now retain the original article URL, title, available summary/content excerpt, feed URL, and publication/update timestamp.
- YouTube trending records retain the source video URL/title and the feed-provided summary/timestamp where present.
- Google Trends records are explicitly marked as discovery signals with no source excerpt; a trend query is not treated as evidence.
- Topic selection carries source metadata forward rather than reducing every item to a headline string.
- src/editorial_qa.py validates source URLs and normalizes evidence records.
- News/current/trending categories are blocked unless at least one HTTP(S) source URL has a source excerpt of at least 120 characters.
- Evergreen/general educational content can proceed without a source excerpt, but its generation instructions prohibit unsupported current events, statistics, prices, legal/tax/medical/financial recommendations, named-person claims, and other time-sensitive facts.
- Script and description prompts receive explicit source-constrained instructions.
- Generated content metadata records source title, URL, publication date, excerpt length, and an honest evidence status.
- Description prompts prohibit invented links, timestamps, and social handles.
- The main orchestrator records an editorial block result instead of silently generating content from unsupported news/trend headlines.

## Mandatory human approval gate
- Every generated package is created with editorial_status=pending_review, editorial_approved=false, and editorial_approval_required=true.
- The orchestrator saves assets with database status pending_editorial_review.
- Publisher.publish_all independently requires editorial_approved=true, a non-empty approved_by identity, and a non-empty approved_at timestamp, in addition to the publishing safety gate.
- A generated model response cannot self-approve. No automatic approval is granted.
- A secure GitHub Actions review workflow and restricted Supabase decision RPC are implemented on the Phase 3 branch. They are not operational until the owner applies the SQL schema and configures the required repository secrets/approver allowlist. Until then, generated assets remain pending review and publishing stays blocked.

## Important distinction
This is a **provenance and eligibility gate**, not a full independent fact-checking system:
- A supplied RSS excerpt may be incomplete or inaccurate.
- A URL being present does not prove the article is authoritative.
- The 120-character threshold is a minimum usefulness heuristic, not proof of correctness.
- The model may still make mistakes; no AI-generated content should be treated as editorially approved.
- Human review and source comparison remain required before any public release.
- Current/trending topics without adequate excerpts are intentionally skipped rather than guessed.

## Regression coverage
Six tests cover:
1. News without source evidence is blocked.
2. News with a URL but a very short excerpt is blocked.
3. News with a URL and a useful excerpt is eligible.
4. Trending topics without source evidence are blocked.
5. Evergreen topics are limited to general education when sources are absent.
6. Source metadata is labelled as supplied but not independently verified.

## Relevant files
- src/research_engine.py
- src/editorial_qa.py
- src/content_generator.py
- src/main.py
- tests/test_pipeline_safety_and_reports.py

## Release gate
Do not enable live publishing solely because these tests pass. The system still needs manual editorial approval, a valid Gemini key if Gemini is to be used, controlled inference verification, and a confirmed commercial workflow.


## Phase 3 review integrity controls
- The review package now stores description, hashtags and thumbnail prompt alongside title/script and source metadata.
- SHA-256 fingerprint binds the exact reviewed text and source references; edits invalidate the supplied fingerprint.
- The GitHub workflow displays a review package first. A separate approve/reject dispatch records a decision, so a reviewer can inspect before deciding.
- The workflow validates the authenticated GitHub actor against a repository variable; reviewer identity is not accepted as a free-form input.
- A Supabase RPC performs a row lock, status/hash checks, status update and audit insert in one transaction.
- Audit events are append-only through a database trigger. The function is SECURITY INVOKER and execution is granted only to service_role.
- The workflow records editorial approval only. It does not publish and does not switch on the publishing gate.
- Review remains not production-operational until the SQL is applied and repository settings are configured by the owner.
