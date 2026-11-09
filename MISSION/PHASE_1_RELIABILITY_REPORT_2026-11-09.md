# Phase 1 Reliability Report — 2026-11-09

## Status

**Code changes:** built on isolated branch  
**Production deployment:** not deployed; `master` unchanged  
**Automated validation:** passed  
**Actual revenue:** ₹0 verified

Branch: `revenue-engine/phase-1-reliability`  
Compare: https://github.com/manish91082-coder/ai-content-system/compare/master...revenue-engine/phase-1-reliability

## 1. Root causes confirmed from run #17

Evidence: https://github.com/manish91082-coder/ai-content-system/actions/runs/42472519954

- Telegram report formatter iterated over topic-level nested dictionaries as if each value were a flat platform result. It attempted to slice a dictionary as a string and raised `TypeError: slice(None, 50, None)`.
- Gemini request returned an unauthenticated error. The log confirms that the secret environment variable was non-empty, but it does not establish that the key was valid.
- Groq request returned HTTP 400 / BadRequestError. Source code used `llama-3.1-70b-versatile`, a model ID whose official Groq deprecation page says it was shut down on 2025-01-24.
- Telegram credentials were not configured in the observed run.
- Research obtained RSS headlines, but the pipeline had no full evidence/provenance package attached to each headline before script generation.

## 2. Implemented on isolated branch

- Rewrote report formatting to safely handle nested topic/platform results, non-dictionary values, and nested errors.
- Added `src/publish_guard.py`. Publishing is fail-closed: `PUBLISH_ENABLED=true` AND `TEST_MODE=false` are both required.
- Enforced the same authorization check in both the orchestrator and Publisher, providing defense in depth.
- Changed manual workflow default to test mode ON. The separate `PUBLISH_ENABLED` repository secret is required before any external post can occur.
- Added automated tests and an isolated test-only workflow.
- Migrated default Gemini model identifier to `gemini-3.8-flash`.
- Migrated default Groq model identifier to `openai/gpt-oss-120b`.
- Made model identifiers configurable through `GEMINI_MODEL` and `GROQ_MODEL`.
- Replaced anti-detection editorial wording with reader-value, factuality, and no-fabricated-experience requirements.
- Improved provider error logging to preserve useful exception details without logging secret values.

## 3. Automated verification

Validation workflow: https://github.com/manish91082-coder/ai-content-system/actions/runs/42634152363

- Python source compilation: passed.
- Unit tests: passed, 9 tests total.
- Test coverage includes fail-closed publishing behavior and nested Telegram report formatting.
- No social publishing was attempted by the validation workflow.
- No AI provider credentials were read by the validation workflow.

## 4. Current provider evidence and constraints

- Groq official deprecation history confirms `llama-3.1-70b-versatile` was shut down on 2025-01-24. The current official model catalogue and free-tier rate-limit documentation must be checked before each production model selection.
- Groq current free-tier options include `openai/gpt-oss-120b`; per-model limits apply and may change.
- Google's Gemini Developer API currently lists `gemini-3.8-flash` with a free tier. Google states free-tier content may be used to improve products. Do not send confidential customer information through that tier.
- OpenRouter's free model access is rate-limited (50 requests/day on Free, with 20 requests/minute on free variants). It is a possible backup, not an unlimited production dependency.
- Free tiers are best-effort and not production SLAs. The pipeline must gracefully stop when limits are reached.

## 5. Remaining blockers

1. Gemini key authentication still requires account-side verification/replacement by the operator. Never paste the key into chat or commit it.
2. Groq request must be smoke-tested using the current model after the operator confirms the secret is valid. The exact historical 400 response body was not preserved in run #17, so the old model ID is a verified defect but may not be the only cause.
3. RSS research must store source URL, publication timestamp, extracted evidence, and citation/provenance before generating factual scripts.
4. Full pipeline integration test is still pending. The isolated unit-test workflow does not prove that Gemini/Groq generation, image/voice/video creation, or real publishing works.
5. Telegram is optional but should be configured only if the operator wants notifications.
6. Supabase RLS policy review and secret-history scan remain open.
7. No checkout, product catalogue, customer fulfilment, affiliate attribution, refund handling, or bank-settlement ledger exists yet.

## 6. Release policy

Do not merge this branch to `master` yet. The branch is technically validated at unit-test/compile level, but provider authentication and full end-to-end generation remain unverified. Publishing stays blocked unless both explicit authorization gates are set.

## Evidence links

- Groq model deprecations: https://console.groq.com/docs/deprecations
- Groq supported models: https://console.groq.com/docs/models
- Gemini API pricing and free-tier terms: https://ai.google.dev/gemini-api/docs/pricing
- OpenRouter free model limits: https://openrouter.ai/collections/free-models/
