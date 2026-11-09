# Phase 1 and Phase 2 Engineering Checkpoint

**Date:** 2026-11-09  
**Branch:** revenue-engine/phase-1-safety-fixes  
**Scope:** isolated reliability, publishing safety, provider diagnostics, and editorial evidence improvements. No production deployment and no live publishing.

## 1. Pipeline reliability and publishing safety

- Telegram report formatting now handles nested topic/platform/result structures, malformed payloads, and HTML escaping.
- Startup/report wording no longer equates content generation with publishing.
- Publishing requires both PUBLISH_ENABLED=true and TEST_MODE=false.
- The publisher has its own fail-closed guard.
- Scheduled daily runs force TEST_MODE=true.
- Regression tests cover the safety gate and report formatting.

## 2. Provider integration and diagnostics

- Migrated from the deprecated Google generativeai SDK to the maintained google-genai SDK.
- Updated Gemini and Groq model defaults based on the model catalogue reviewed for this branch.
- Reconciled dependency conflicts by upgrading Supabase, HTTPX, and Groq SDK versions.
- Added a metadata-only provider check. It lists models/authenticates credentials without sending an inference prompt.
- Added a provider circuit breaker for permanent authentication/model errors.

### Observed provider state
- Groq: key authentication succeeded and openai/gpt-oss-120b was listed.
- Gemini: configured secret failed with HTTP 401 UNAUTHENTICATED / ACCESS_TOKEN_TYPE_UNSUPPORTED. Google response says the API key is invalid or unsupported. Replace the GitHub Actions GEMINI_API_KEY secret with a valid Google AI Studio Gemini Developer API key. Do not paste secrets into chat or source code.
- No provider inference request was made by the metadata-only check. Billing tier and remaining quota were not established.

## 3. Source provenance and editorial evidence gate

- RSS research records retain original article URL, title, feed URL, available excerpt and publication/update timestamp.
- YouTube trend records retain the feed-provided URL/title/summary/date.
- Google Trends is labelled as a discovery signal without source evidence.
- Topic selection preserves source metadata.
- News/current/trending topics are rejected unless a valid HTTP(S) source URL and a source excerpt of at least 120 characters are supplied.
- Evergreen/general educational content may proceed without a source excerpt, but generation instructions prohibit unsupported current events, statistics, prices, legal/tax/medical/financial recommendations, named-person claims and other time-sensitive assertions.
- Generated scripts and descriptions receive source-constrained instructions.
- Content metadata records source URL/title/date and an honest evidence status.
- Description prompts prohibit invented links, timestamps and social handles.

This is a provenance and eligibility gate, not independent fact-checking. A URL or RSS excerpt does not establish source authority or truth. Human editorial review remains mandatory before public release.

Detailed design: MISSION/EDITORIAL_EVIDENCE_GATE.md

## 4. Automated verification

GitHub Actions CI run #18:
https://github.com/manish91082-coder/ai-content-system/actions/runs/42650422406

- Dependency installation: passed.
- Python compile checks: passed.
- Regression suite: 19 tests passed.
- Metadata-only provider check: completed in degraded state.
- Groq authentication/model listing: passed.
- Gemini authentication: failed due to invalid/unsupported configured key.

Earlier CI runs exposed and helped resolve dependency conflicts. The current run verifies the source-provenance gate and all 19 tests on the branch code as of commit 0d14f6ec877083507252929121f27d60c6f749c8.

## 5. PR and deployment status

- Draft PR #1: https://github.com/manish91082-coder/ai-content-system/pull/1
- Base: master
- Head: revenue-engine/phase-1-safety-fixes
- PR remains draft and unmerged.
- No production deployment or live social publishing occurred.
- Scheduled publishing remains disabled by TEST_MODE=true.
- Actual settled revenue remains ₹0 until settlement evidence exists.

## 6. Remaining release blockers

1. Account owner must replace the invalid Gemini secret, if Gemini is to remain enabled.
2. Confirm provider billing tier/free quota and run a controlled inference test only after confirming no unexpected charge.
3. Add stronger source retrieval, source authority assessment, cross-source corroboration, and human editorial approval.
4. Redesign Supabase row-level security before production data use.
5. Build product catalogue, checkout, order state machine, delivery, refunds, attribution, and settlement reconciliation.
6. Validate one narrow customer offer with a real paid pilot before broad automation.

## 7. Next execution order

1. Wait for a valid Gemini secret or continue with Groq only after its account quota and billing status are confirmed.
2. Build a source authority and cross-check layer beyond RSS excerpt provenance.
3. Build an editorial review/approval queue; never auto-publish unreviewed content.
4. Select one narrow business segment using primary customer evidence.
5. Implement checkout and automated fulfilment only after a paid pilot validates demand.
