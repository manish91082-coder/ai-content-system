# Case Study: Repairing a Failing AI Content Pipeline

**Project type:** Python + GitHub Actions + LLM API workflow  
**Status:** reliability changes tested on an isolated branch; not merged to production  
**Evidence date:** 2026-11-09

## The problem

A scheduled AI content pipeline could complete its research stage but fail during content generation and final reporting.

The observed GitHub Actions run showed:
- Research data was collected and saved.
- Gemini returned an authentication error.
- Groq returned a bad request error.
- Three content-generation attempts failed.
- The final Telegram report crashed while handling nested result data.
- The run provided no evidence of successful social publishing.

## Root-cause analysis

1. The report formatter treated a nested dictionary as a string and attempted a slice operation.
2. The Groq client referenced a model identifier that Groq had already retired.
3. The orchestrator passed a test-mode input but did not enforce a publishing authorization check before calling the publisher.
4. The content pipeline did not yet have an end-to-end evidence trail for provider authentication and media generation.

## Engineering changes

- Reworked report formatting to handle nested topic and platform results safely.
- Added regression tests for nested success, nested error, malformed result, and empty result cases.
- Added a fail-closed publishing authorization module.
- Enforced publishing authorization in both the orchestrator and the publisher.
- Made manual workflow runs default to test mode.
- Required a separate explicit publishing enable flag before any social publishing can occur.
- Updated model defaults and made them configurable through environment variables.
- Added a validation workflow that compiles the Python source and runs unit tests.

## Verification

The isolated validation workflow completed successfully:
- Python compilation: passed.
- Unit tests: 9/9 passed.
- No AI provider credentials were read by the validation workflow.
- No external publishing was attempted by the validation workflow.

Evidence:
- Original failed run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42472519954
- Reliability validation run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42634152363
- Engineering branch: https://github.com/manish91082-coder/ai-content-system/tree/revenue-engine/phase-1-reliability

## What this case study does not claim

- The full AI provider integration has not yet passed an authenticated smoke test.
- Media generation has not been verified end to end on the repaired branch.
- Social publishing has not been enabled or tested.
- The branch has not been merged into the production/default branch.
- No customer order, customer outcome, or revenue is claimed.

## Transferable lesson

AI automation reliability is not just about selecting a model. A production workflow needs observable failure states, supported model identifiers, regression tests, secure credential handling, and explicit approval gates before external actions.
