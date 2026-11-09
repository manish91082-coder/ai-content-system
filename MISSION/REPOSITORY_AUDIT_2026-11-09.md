# Repository Audit — 2026-11-09

## Repository identity

- Repository: `manish91082-coder/ai-content-system`
- URL: https://github.com/manish91082-coder/ai-content-system
- Default branch: `master`
- Visibility: **Public** (confirmed through connected GitHub account and Actions run metadata)
- Size reported by GitHub: approximately 50 KB
- Branches observed: `master`, `zero-cost-model-reliability-fix`
- The second branch is identical to `master` at the audit checkpoint (0 commits ahead/behind).
- Audit branch: `revenue-engine/phase-0-audit`

## Inventory observed on master

- `.github/workflows/daily_content.yml`
- `.github/workflows/research_only.yml`
- `README.md`, `SETUP_GUIDE.md`, `requirements.txt`, `.gitignore`
- `config/content_rules.json`, `config/supabase_schema.sql`
- `src/main.py`, `src/research_engine.py`, `src/content_generator.py`
- `src/image_generator.py`, `src/voice_generator.py`, `src/video_creator.py`
- `src/publisher.py`, `src/database.py`, `src/telegram_bot.py`

No test suite, product checkout, order ledger, affiliate attribution, customer fulfilment workflow, or settlement reconciliation implementation was visible in the recursive tree at this checkpoint.

## Verified runtime evidence

Latest 20 Actions runs were inspected on 2026-11-09:
- Research Engine Test run #26: completed successfully on 2026-11-09.
- Daily AI Content Pipeline run #17: failed on 2026-11-08.
- Daily pipeline runs #10–#17 observed as failures in the latest 20-run list.
- Research workflow runs in that list completed successfully.

Run #17 job log shows:
- Dependency installation and runner setup completed.
- Research ran and saved topics to Supabase.
- Google Trends returned HTTP 404 in that run; RSS supplied the usable topics.
- Gemini returned an unauthenticated error.
- Groq returned a bad request error.
- Telegram credentials were unavailable.
- All three content-generation attempts failed.
- The daily reporting path then raised a runtime error: `slice(None, 50, None)`.
- No successful publishing evidence was present in that run.

Therefore, research workflow success is not evidence of generated media, published posts, audience growth, or revenue.

## Technical / product blockers

1. API configuration is not healthy: the latest main pipeline log records Gemini authentication and Groq request failures.
2. Telegram reporting is not configured in the observed run.
3. The pipeline's error handling continues after individual topic failures, but its final reporting path can itself fail.
4. `TEST_MODE` is passed by workflow but the reviewed orchestration path does not visibly enforce a no-publish guard before publisher invocation.
5. Current video composition uses a repeated still image for long-form output; this is not yet an editorial-quality video pipeline.
6. The content prompt includes an “anti-AI-detection” framing. Replace with quality, originality, factuality, and disclosure requirements; do not attempt to evade platform detection.
7. The RSS research path collects headlines but lacks a documented fact-check/provenance pipeline before scripts are generated.
8. The repository does not currently implement checkout, products/offers, customer fulfilment, affiliate/referral attribution, or actual bank-settlement reconciliation.
9. Supabase schema policies must be reviewed carefully before use. The current SQL defines broad `FOR ALL USING (true)` policies. Do not deploy this schema as-is without an explicit role/grant review and restrictive policies.
10. The setup guide contains a personal account email in a public file. Replace it with a neutral placeholder. A normal file edit does not erase historical copies from Git history.

## Strategic disposition

**Decision: keep the repository Public for now, but do not treat it as production-ready.**

Reasons:
- GitHub-hosted standard runner minutes are free for public repositories; private repositories use plan quotas.
- Public visibility may later support open-source credibility and organic developer distribution.
- No API keys were observed in the fetched source files, but a full secret-history scan is not available from this audit.
- Public code must be treated as fully visible. No credentials or customer data may be committed.

## Next engineering gates

1. Sanitize the public setup guide and audit the repository history for secrets/PII.
2. Add automated tests and a strict `TEST_MODE` publishing guard.
3. Repair and validate AI-provider fallback with current supported model identifiers and useful error classification.
4. Fix final reporting and Telegram optionality.
5. Replace low-quality / unsupported content production assumptions with source citations, editorial QA, and original value.
6. Build a separate revenue layer: offer catalogue, checkout integration, order events, fulfilment, partner attribution, refund handling, and settlement ledger.
7. Do not activate public posting until content and platform-permission gates pass.

## Evidence links

- Repository: https://github.com/manish91082-coder/ai-content-system
- Latest research run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42576717428
- Latest failed daily run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42472519954
- GitHub Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
