# Nexus Cloud Work Engine — Phase 1 (Read-only multi-marketplace)

Zero-cost-first cloud marketplace discovery using GitHub Actions and Python standard library only.

## Connected public discovery adapters
- **MoltJobs:** public jobs endpoint with funded=true; platform referral/forum reward listings are excluded from ordinary paid work.
- **Dealwork:** public GET /api/v1/jobs?per_page=20&sort=newest. Live records expose status, jobMode, posterFunded, claimBlockedReason, fixedPrice, budgetMin, budgetMax, eligibleWorkerTypes, and posterType. Listings with posterFunded=false or underfunded/unfunded blockers are blocked.
- **Taskmarket:** public GET /api/tasks?status=open&limit=50&sort=newest. Six-decimal base-unit rewards are normalized while raw units are retained. escrowTxHash is only a reference requiring independent chain/terms verification, not proof of verified escrow.

## Verified latest cloud run
- GitHub Actions run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42894478350
- Result: success. Unit tests, all three read-only adapters, and artifact upload succeeded.
- Report artifact: nexus-funded-jobs-42894478350.
- Latest scan: 35 listings discovered (10 MoltJobs, 20 Dealwork, 5 Taskmarket).
- MoltJobs: 10 referral/forum reward listings excluded.
- Dealwork: 20 listings blocked because posterFunded=false; no funded work in this sample.
- Taskmarket: 5 open listings with escrow transaction references. A subsequent cloud run fetched canonical details and settlement terms, then verified all 5 transaction receipts on the correct public RPCs. Each successful receipt included a payment-token Transfer to the correct Taskmarket Diamond equal to the listed reward. This proves the listed reward was deposited to the contract address, not that a worker will win or be paid.

## Safety and economics
No registration, bids, claims, pitches, submissions, wallet actions, or payments are performed. Unknown funding, platform permissions, model/compute costs, settlement fees, acceptance risk, and India withdrawal route remain unknown. Economic gate is not evaluated. A listed reward is not income.

## Runtime
- GitHub Actions on a public repository; hosted runners are subject to GitHub policy and usage limits.
- Hourly best-effort scan plus manual dispatch and path-filtered push validation.
- No API keys, secrets, paid model APIs, local laptop, or GPU required for public discovery.
- This is a discovery monitor, not a promise of task availability or earnings.

## Next gate
Assess the five tasks against costs, AI execution feasibility, eligibility and submission fees. The best zero-compute candidate is a 1 OUSD economics article, but its listing already has 42 submissions; Taskmarket documentation says the first five bounty submissions are free and later submissions cost 0.001 OUSD. No wallet is authorized or funded, so do not submit or spend.


## Phase 3 — Bounty cloud worker and hired-work preparation

- Dedicated workflow: .github/workflows/nexus-bounty-agent.yml, manual trigger plus five-minute schedule.
- bounty_agent.py: authenticated read-only Bounty connector; complete cursor pagination, duplicate ID elimination, detail enrichment, fixed payout vs budget separation, active-work discovery, and persistent version tracking.
- task_triage.py: deterministic capability and safety triage. Bid budgets remain estimates, never realized or guaranteed income.
- model_gateway.py: OpenRouter free-model route only (openrouter/free); paid fallback is structurally disabled.
- draft_executor.py: prepares Markdown drafts only for already-hired active work, using the free-only model route. It skips test Bounties, unassigned work, unverified details and tasks with attachments not yet safely ingested. It writes drafts locally to the report artifact and never submits them.
- State cache: .nexus_state/ tracks Bounty versions and draft versions across scheduled workflow runs.
- Read-only Bounty API uses BOUNTY_AGENT_API_KEY; the model route uses OPENROUTER_API_KEY. Both are read from GitHub Actions Secrets. Never put keys in repository files or chat.
- When either secret is absent, the workflow reports a clear idle/readiness state and performs no authenticated calls or paid inference. No marketplace write operation exists in this workflow.
- Schedule is five-minute best-effort polling (not the platform's recommended 30 seconds); event/webhook support is a later extension. GitHub scheduling can be delayed by platform load.

### Current verified cloud run
- Dedicated Bounty workflow run 42898672894 passed all 27 tests and all discovery/triage/readiness/draft steps.
- Its artifact showed needs_agent_api_key, candidate_count=0, drafts_created=0, and no marketplace writes. This is a clean idle state, not a claim that the platform has no tasks.
- Later scanner test failures were caused by an outdated reason-string assertion; classifier output was corrected. Verify the newest runs before assuming subsequent changes are green.

### Non-negotiable economic and execution rule
A budget field in a bid-flow Bounty is only a pricing signal. Only the accepted bid's payout_cents is the agent's payout amount; test Bounties move no money. Draft generation is not submission, acceptance, or revenue. Realized income is counted only after settlement and an independently reconciled payout.
