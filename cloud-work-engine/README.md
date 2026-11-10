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
