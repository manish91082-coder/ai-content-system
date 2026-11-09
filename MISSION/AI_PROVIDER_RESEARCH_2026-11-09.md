# AI Provider Reliability Research — 2026-11-09

## Executive decision

Use Gemini Developer API's free-tier `gemini-3.5-flash-lite` as primary and Groq Free plan's `openai/gpt-oss-120b` as fallback, subject to each account's live quota and model availability. Do not configure a paid billing tier. If a provider returns a billing/limit error, stop and preserve a no-cost fallback path.

## Verified provider findings

### Google Gemini
- Google recommends the maintained `google-genai` Python SDK. The legacy `google-generativeai` Python library is not actively maintained and was deprecated on 2025-11-30.
- Official model catalogue lists `gemini-3.5-flash-lite`; the official pricing page lists its Standard input and output as free of charge on the Free Tier.
- Free tier is limited to selected models and usage limits vary by project/account tier. The exact live quotas must be checked in AI Studio; do not hardcode a universal RPD/RPM value.
- Google says content submitted to unpaid services may be used to improve products and may be reviewed by human reviewers. Do not submit confidential, personal, or sensitive information to this free tier.

### Groq
- Official model catalogue lists `openai/gpt-oss-120b` and `openai/gpt-oss-20b`.
- The official rate-limits page's free-plan table lists `openai/gpt-oss-120b` at 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD. Exact account limits can vary and should be checked in the Groq Console.
- Groq's billing FAQ distinguishes the Free tier from the paid Developer tier. Upgrading to Developer requires a valid payment method and enables paid usage; this mission must remain on Free.
- Groq's model deprecation history demonstrates that model IDs can be shut down; the application must keep model IDs configurable and log the active ID.

## Code changes based on this research
- Gemini SDK migrated to `google-genai==2.33.0`.
- Gemini default model changed to `gemini-3.5-flash-lite`, overridable through `GEMINI_MODEL`.
- Groq default model changed to `openai/gpt-oss-120b`, overridable through `GROQ_MODEL`.
- Error logs now include exception class and a bounded, redacted message rather than collapsing every provider error into a generic failure.
- Provider selection is configurable without editing code.

## Root-cause interpretation of the previous run
- Gemini's `Unauthenticated` response is evidence of an authentication/credential problem. Changing the model ID or SDK cannot make an invalid/revoked/mis-scoped key valid. The GitHub secret value was not inspected. If the new SDK still reports authentication failure, the account owner must create/verify a valid Gemini API key in Google AI Studio and replace the GitHub Actions secret without pasting the key into chat or source code.
- Groq's `BadRequestError` is consistent with the old hard-coded model identifier being unavailable. The current default is a model listed by Groq's current catalogue and Free-plan limits table. A live request still needs to be tested with the account's key.

## Primary official references
- Google model catalogue: https://ai.google.dev/gemini-api/docs/models
- Google pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google SDK libraries and legacy SDK status: https://ai.google.dev/gemini-api/docs/libraries
- Google SDK migration guide: https://ai.google.dev/gemini-api/docs/migrate
- Google Gemini API unpaid-service data terms: https://ai.google.dev/gemini-api/terms
- Groq supported models: https://console.groq.com/docs/models
- Groq free-plan rate limits: https://console.groq.com/docs/rate-limits
- Groq model deprecations: https://console.groq.com/docs/deprecations
- Groq billing FAQ: https://console.groq.com/docs/billing-faqs

## Limits of this verification
- Provider account credentials and live account quotas were not accessed.
- No API key value was read or printed.
- No provider inference request was made from this environment.
- A successful SDK import or client construction is not proof of valid authentication or model entitlement.
- Full GitHub Actions regression execution remains pending.
