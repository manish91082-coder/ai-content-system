# Nexus Cloud Work Engine — Phase 1 (Read-only)

Zero-cost-first cloud marketplace monitor. This phase discovers public MoltJobs listings and records jobs explicitly returned by the API funded=true filter. It does NOT register an agent, bid, claim work, submit deliverables, access a wallet, or move funds.

## Runtime
- GitHub Actions on a public repository; standard hosted runners are free for public repositories subject to GitHub policy and limits.
- Hourly best-effort scan plus manual dispatch.
- Python standard library only. No API key, secrets, paid model, local laptop, or GPU required.

## Why read-only first
A listing is not proof of escrow funding or payment. Settlement details must be reconciled before wallet operations. This scanner never spends bid credits or starts speculative work.

## Output
Each run creates a JSON report and uploads it as a workflow artifact. An empty funded board is a valid finding, not a failure.

## Limits
Public API visibility only; no authenticated agent profile; no bidding or delivery; schedules are best-effort. This is monitoring infrastructure, not a promise of work or income.

## Next gate
Verify live schema, settlement chain, owner/KYC requirements, funding, and acceptance rules before designing an authenticated executor. API keys must be stored only in GitHub Actions Secrets, never committed.
