# Phase 1 — Reliability and Publishing Safety Remediation

**Date:** 2026-11-09  
**Branch:** `revenue-engine/phase-1-safety-fixes`  
**Scope:** isolated code changes only. No production/default-branch deployment and no live publishing.

## 1. Confirmed defect and remediation

The 2026-11-08 Daily Pipeline run #17 failed after topic generation attempts because the report formatter treated nested per-topic publishing dictionaries as strings and sliced them with `[:50]`. The resulting exception was `slice(None, 50, None)`.

Changes made:
- `src/telegram_bot.py`: report formatting now understands topic → platform → result nesting, handles legacy flat results and malformed values, escapes dynamic HTML content, and does not claim that generated assets were published.
- `src/main.py`: records publishing as blocked when the safety gate is closed; does not call `publisher.publish_all` in that state; only records actual publisher result dictionaries.
- `src/pipeline_safety.py`: publishing requires both `PUBLISH_ENABLED=true` and `TEST_MODE=false`. Missing or malformed values block publishing.
- `.github/workflows/daily_content.yml`: scheduled executions force test mode; live publishing additionally requires the repository variable `PUBLISH_ENABLED` to be explicitly set to true.
- `tests/test_pipeline_safety_and_reports.py`: ten regression tests cover default-deny behavior, explicit gate conditions, nested/legacy reporting, malformed payloads, and HTML escaping.
- Workflow now runs Python compile checks, unit tests, and metadata-only provider credential/model checks before the content pipeline.
- `groq` SDK upgraded to 1.7.0 after CI exposed `Client.__init__() got an unexpected keyword argument 'proxies'` in 0.11.0 with HTTPX 0.28.1.
- Provider circuit breaker disables a provider for the remainder of a run after permanent 401/403/404 or model-not-found failures, avoiding repeated failed calls.

## 2. Safety semantics

Publishing is allowed only when both conditions are true:
- Repository variable `PUBLISH_ENABLED` is explicitly `true`.
- Runtime environment `TEST_MODE` is explicitly false.

Scheduled runs force `TEST_MODE=true`. The repository variable has not been enabled by this work. No live social publishing was attempted.

## 3. Verification status

- GitHub Actions CI run #10 succeeded: full dependencies installed, compile checks passed, all 13 tests passed, and provider catalogue check completed. Run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42649140264
- Groq credential authentication and `openai/gpt-oss-120b` model listing were confirmed using metadata-only API calls.
- Gemini secret exists but is invalid for the Gemini Developer API: HTTP 401 `UNAUTHENTICATED`, reason `ACCESS_TOKEN_TYPE_UNSUPPORTED`. No key value was exposed. This appears to be an OAuth token or otherwise unsupported/invalid key type; replace with a valid Google AI Studio API key.

- Dedicated GitHub Actions CI run #3 succeeded: dependency installation, Python source/test compilation, and all 10 regression tests passed. Run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42648302328
- The first two CI attempts exposed real dependency conflicts: Google GenAI required HTTPX >=0.28.1 while Supabase 2.9.1 required HTTPX <0.28. The dependency set was reconciled by moving to Supabase 2.34.1 and HTTPX 0.28.1. The successful third run installed the full requirements set cleanly.

## 4. Verification status

- Source changes committed to the isolated branch.
- GitHub Actions CI run #3 passed all 10 regression tests and Python compile checks.
- Full automated CI test suite has now run successfully on the isolated branch. No live provider inference or social publishing has been run.
- No PR merged; no changes deployed to `master`.
- No production API secret values were inspected or changed. Secret names were present; only provider API responses were observed.

## 5. Known remaining blockers

- Gemini authentication remains unresolved and requires the account owner to replace the invalid `GEMINI_API_KEY` secret. Groq key and target model are verified at catalogue/authentication level; no inference request was made.
- Telegram credentials were absent in the observed run; reporting is now safer but delivery remains unconfigured.
- Research source verification, fact-checking and provenance need implementation.
- Supabase schema's broad RLS policies need security redesign before production use.
- No checkout, product catalogue, order/fulfilment, affiliate attribution, refunds, or settlement ledger exists yet.

## 6. Provider migration findings

- Gemini's previous model ID `gemini-2.0-flash-exp` is no longer a suitable default; Google's current catalogue recommends newer model IDs. The legacy `google-generativeai` Python SDK is deprecated/not actively maintained.
- Gemini SDK migrated to `google-genai==2.33.0`; default model is `gemini-3.5-flash-lite`, which Google's current pricing page lists as free on the Free Tier.
- Groq's previous hard-coded model ID `llama-3.1-70b-versatile` was replaced with `openai/gpt-oss-120b`, which is in the current model catalogue and free-plan rate-limit table.
- Gemini's previous `Unauthenticated` response remains a credential issue until a valid API key is confirmed. No secret value was inspected. If authentication still fails, the owner must verify/replace the GitHub secret privately.
- Google unpaid-tier content may be used to improve Google products and reviewed by human reviewers. Do not submit confidential or personal data.
- Full details and official source links: `MISSION/AI_PROVIDER_RESEARCH_2026-11-09.md`.

## 7. Pull request status

- Draft PR #1: https://github.com/manish91082-coder/ai-content-system/pull/1
- Base: `master`; head: `revenue-engine/phase-1-safety-fixes`.
- GitHub reports the draft PR as clean/mergeable. It remains unmerged and no production deployment has occurred.

## 8. Next gate

1. Run the regression workflow on this branch and inspect exact test results.
2. Diagnose the provider failures with current official provider documentation and non-secret configuration checks.
3. Add source provenance and editorial QA.
4. Only then evaluate a first revenue offer and payment/delivery workflow.
