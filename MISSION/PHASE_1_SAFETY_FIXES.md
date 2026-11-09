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
- `tests/test_pipeline_safety_and_reports.py`: nine regression tests cover default-deny behavior, explicit gate conditions, nested/legacy reporting, malformed payloads, and HTML escaping.
- Workflow now runs Python compile checks and unit tests before the content pipeline.

## 2. Safety semantics

Publishing is allowed only when both conditions are true:
- Repository variable `PUBLISH_ENABLED` is explicitly `true`.
- Runtime environment `TEST_MODE` is explicitly false.

Scheduled runs force `TEST_MODE=true`. The repository variable has not been enabled by this work. No live social publishing was attempted.

## 3. Verification status

- Source changes committed to the isolated branch.
- Eight equivalent logic/report sanity checks were exercised in the assistant's local analysis environment and passed.
- Full repository test suite and GitHub Actions execution have **not yet been run**. The execution environment could not clone the public GitHub repository because network DNS resolution failed. The new workflow test step will run on the next authorized GitHub Actions execution.
- No PR merged; no changes deployed to `master`.
- No production API credentials were inspected or changed.

## 4. Known remaining blockers

- Gemini authentication and Groq request errors from run #17 remain unresolved. Current provider/model identifiers and credential validity require separate verification.
- Telegram credentials were absent in the observed run; reporting is now safer but delivery remains unconfigured.
- Research source verification, fact-checking and provenance need implementation.
- Supabase schema's broad RLS policies need security redesign before production use.
- No checkout, product catalogue, order/fulfilment, affiliate attribution, refunds, or settlement ledger exists yet.

## 5. Next gate

1. Run the regression workflow on this branch and inspect exact test results.
2. Diagnose the provider failures with current official provider documentation and non-secret configuration checks.
3. Add source provenance and editorial QA.
4. Only then evaluate a first revenue offer and payment/delivery workflow.
