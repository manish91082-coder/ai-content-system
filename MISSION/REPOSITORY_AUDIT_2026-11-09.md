# Repository Audit — 2026-11-09 (updated Phase 1 checkpoint)

## Repository identity
- Repository: `manish91082-coder/ai-content-system`
- URL: https://github.com/manish91082-coder/ai-content-system
- Default branch: `master`
- Visibility: Public
- Phase 1 working branch: `revenue-engine/phase-1-safety-fixes`
- Phase 1 code changes are isolated; no PR merged and no production deployment.

## Baseline runtime evidence
Latest observed Daily AI Content Pipeline run #17 failed on 2026-11-08. Its logs show:
- Research ran and saved five topics.
- Google Trends returned HTTP 404; RSS provided limited topics.
- Gemini request failed with an unauthenticated error.
- Groq request failed with a bad-request error.
- Telegram credentials were unavailable.
- All three content-generation attempts failed.
- Final report then crashed with `slice(None, 50, None)`.
- No successful publishing evidence in that run.

## Phase 1 code changes on isolated branch
1. `src/telegram_bot.py`: nested report formatter, legacy flat result support, malformed result handling, HTML escaping.
2. `src/pipeline_safety.py`: fail-closed publishing gate. Requires explicit `PUBLISH_ENABLED=true` and `TEST_MODE=false`.
3. `src/publisher.py`: duplicates the gate inside `publish_all` to prevent bypass through a direct publisher call.
4. `src/main.py`: does not call publisher while gate is closed; reports blocked publishing distinctly.
5. `.github/workflows/daily_content.yml`: scheduled runs force test mode; explicit repository variable gates live publishing; compile and unit tests run before pipeline.
6. `tests/test_pipeline_safety_and_reports.py`: ten regression tests.
7. `src/content_generator.py` and `requirements.txt`: migrated from the deprecated Gemini SDK and retired model IDs to current free-tier model identifiers.

## Provider research
- Gemini: maintained `google-genai` SDK and `gemini-3.5-flash-lite` selected from current official model/pricing docs.
- Groq: `openai/gpt-oss-120b` selected from current official model catalogue and free-plan rate-limit table.
- Gemini authentication failure still requires a valid account key; no secret was read. Provider quota and actual model access are not yet runtime-verified.
- Gemini free-tier content may be used for product improvement and human review; do not send sensitive or confidential material.
- Full source links: `MISSION/AI_PROVIDER_RESEARCH_2026-11-09.md`.

## Verification status
- GitHub Actions CI run #10 succeeded: dependencies installed, compile checks passed, all 13 regression tests passed, and metadata-only provider checks completed. Run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42649140264
- CI runs #1 and #2 exposed dependency conflicts; these were resolved by upgrading Supabase to 2.34.1, HTTPX to 0.28.1, and Groq SDK to 1.7.0.
- Provider check confirms Groq key authentication and target model availability. Gemini secret exists but fails with HTTP 401 `UNAUTHENTICATED` / `ACCESS_TOKEN_TYPE_UNSUPPORTED`; the key value was never accessed.

- No production publish action was attempted.
- The repository variable `PUBLISH_ENABLED` was not enabled.
- No changes from this branch have been merged into `master`.

## Remaining risks / blockers
- Gemini key must be replaced by the account owner. Groq authentication and model catalogue are verified; actual inference remains untested to avoid unknown paid-tier charges. Secret values must never be printed.
- Telegram delivery remains unavailable until configured by the account owner.
- RSS headlines need source provenance and fact-checking before content generation.
- Supabase schema contains broad RLS policies and must be redesigned before production use.
- No checkout, offers, order events, fulfilment, refunds, affiliate attribution or bank settlement reconciliation.
- README marketing claims overstate verified production readiness and should be revised in a later documentation pass.

## Evidence
- Latest research run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42576717428
- Latest failed daily run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42472519954
