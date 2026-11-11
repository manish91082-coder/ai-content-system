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

## Additional public marketplace discovery

- BountyBoard: public open-bounty API added in cloud-work-engine/bountyboard_public.py. It requires no API key for public discovery. The adapter is read-only, cursor-aware, deduplicates IDs, records machine-readable escrow/AI eligibility signals, and estimates the worker payout after the published 10% fee. It never bids or claims. Missing machine-readable proof stays REVIEW_REQUIRED.
- AgentMesh was screened and excluded from the cash-earning pipeline: its own pricing page states credits are not cryptocurrency, cannot be withdrawn, and no real-money payment flow exists. It can be used only for reputation/testing, not revenue.
- Latest BountyBoard public homepage evidence: 6 open bounties; the visible sample is mostly geolocation/iPhone/photo tasks, and a $1 writing-schoolwork task. The latter is excluded for academic-integrity risk. Current open sample has no qualified autonomous cash candidate.
- BountyBoard documents a 10% approval-only fee and Stripe Express payout onboarding; supported bounty currencies are USD, EUR, PLN, CZK and HUF. India-specific connected-account approval is not yet verified. Treat its escrow claims as platform-reported until independent payout history is reconciled.
- BountyBoard Terms (last updated 17 July 2026) include a placeholder legal-jurisdiction section, so account/contract onboarding remains deferred pending legal/operator review.


## Phase 4 — MoltJobs all-open discovery and escrow transition watch

- Primary scanner now queries both the full public open MoltJobs feed and the funded=true feed, paginates and deduplicates across both. A funded search filter is never accepted as independent escrow proof; explicit funded, escrowTxHash, and payment status fields are preserved.
- cloud-work-engine/moltjobs_watchlist.py converts only independent open marketplace jobs into a prioritized watchlist. It excludes referral/forum rewards, low-value cash items, regulated investment/asset-management assignments, and non-marketplace tasks.
- Watchlist state is persisted in .nexus_state/moltjobs_funding_state.json. A transition to funded=true with a transaction hash is emitted as ESCROW_BECAME_FUNDED. That event still requires chain receipt verification and authorized agent assignment; it is not recognized as income.
- Primary hourly workflow now restores/saves this state, runs scanner, builds watchlist, and uploads both report and state artifacts.

### Latest verified MoltJobs result
- GitHub Actions run 42906246301 succeeded; unit tests, all read-only discovery adapters, MoltJobs watchlist build, and artifact upload completed.
- Artifact nexus-funded-jobs-42906246301 (ID 13803779486) contains 58 total records: MoltJobs 18 (10 referral/forum excluded, 8 independent marketplace tasks), Dealwork 20 (unfunded), Taskmarket 4, BasedAgents 16 (10 blocked, 6 excluded).
- Exactly two MoltJobs tasks remain on the high-priority watchlist:
  - WharfUp.com Landing Page — listed budget 150 USDC, 6 acceptance criteria, deadline 2026-11-12 08:11:12 UTC (13:41:12 IST), participation mode BID, funded=false, no escrow transaction/payment status.
  - Landing page for pedex.org — listed budget 150 USDC, 6 acceptance criteria, deadline 2026-11-12 08:10:40 UTC (13:40:40 IST), participation mode BID, funded=false, no escrow transaction/payment status.
- These are budgets in an open bid flow, not secured payments. No claim, bid, account registration, or task submission occurred. Both are watch-only until the original platform changes funding and the agent is validly assigned.
- Remaining six independent MoltJobs tasks were excluded for low budget, missing acceptance criteria, or finance/asset-management/sovereign-wealth/CBDC regulatory exposure.
- The two task details are publicly visible from the listing feed, but private detail reads require a MoltJobs API key; do not invent missing poster messages or full terms.

### Other new public marketplace probes
- WorkPNP: public API currently returns one open task. Its listed 2 USDC reward and competitive bid count make it low-priority; agent onboarding/email-social verification and a wallet are required. No registration or bid.
- BountyBoard.xyz: queried public tasks and stats endpoints returned HTTP 404 from cloud runner. Separate platform docs identify its current Solana Devnet environment; devnet rewards are not counted as income.
- Atelier: public platform endpoints returned HTTP 402 from cloud runner; authenticated/service-owner flow not set up.
- TaskForce: agent task endpoint returned HTTP 401; no API key or agent registration created.
- Agent Souk public API routes were not reachable from cloud runner in this pass. Its payment design is wallet-to-wallet, not escrow; keep lower priority until live demand and counterparties are verified.
- BountyBoard.work public board had only a small set of open tasks, chiefly physical local-photo collection and a schoolwork-like item; excluded from autonomous execution. AgentMesh has non-withdrawable credits and no cash payout.

### Economic rule
A task budget, source feed escrow label, API registration, bid acceptance, or completed work event is not revenue. Only an actual transfer to an authorized payout destination, matched to the task and net of fees/costs, counts as realized income.


## Phase 5 — Local open-weight coder and credential-safe separation

- Replaced the active Bounty workflow OpenRouter dependency with a local CPU model worker. The active workflow no longer requires OPENROUTER_API_KEY.
- Added cloud-work-engine/bundle_active.py. It exports only already-hired work (status=claimed, claim_status=active), with complete task fields and no secrets. Test Bounties, incomplete records and tasks with un-ingested attachments are excluded.
- Added cloud-work-engine/local_coder.py. It uses local Ollama inference with Qwen2.5-Coder 7B on the public GitHub Actions CPU runner. No hosted inference API or model-provider key is used.
- Workflow .github/workflows/nexus-bounty-agent.yml is now a two-job design:
  1. discover-and-triage: carries the Bounty API secret, performs read-only discovery, lifecycle recovery, cash/escrow filtering and exports a sanitized task bundle.
  2. local-cpu-coder: runs only when the sanitized bundle contains an already-hired active task. It receives no Bounty API key, no OpenRouter key and no GitHub write credential.
- The local worker clones a public source repository from a GitHub issue URL, reads a bounded source context, asks the local model for a unified diff, rejects unsafe file paths, secret-file/workflow edits, symlinks, submodules and binary patches, runs git apply --check and git diff --check, then uploads a patch and review note.
- The local coder does not execute task-provided shell commands, tests or arbitrary scripts in this release. It reports test commands recommended by the model as NOT RUN. It never creates PRs, claims, bids, messages or submissions.
- Public GitHub-hosted standard runners are free for public repositories; the local model download/run happens only after the active-work gate is true. Model download/cache optimization remains future work.
- Latest verified Bounty workflow run 42952254773: SUCCESS; 91/91 tests passed; all discovery and reconciliation steps completed; local CPU worker correctly skipped because there was no active hired assignment. No API key was present, so Bounty authenticated reads/events remained in clean idle state.
- Latest verified Jobbi workflow run 42952254948: SUCCESS; 91/91 tests passed; 643 feed records, 324 indexed source-review candidates; 216 met the current higher-confidence cash filter. One live source check returned 404 for a source issue; cached records were retained as unverified, not promoted.
- This worker produces a reviewable patch artifact, not an accepted or paid submission. Revenue remains zero until actual settlement is independently reconciled.

### Bounty credential bootstrap gate
- Current official Bounty documentation says the Agent is created in the Bounty Agents dashboard (New agent), where the privileged Agent API key is generated. Complete the Agent Card, then store the key server-side as BOUNTY_AGENT_API_KEY. The documented connection flow requires account-owner dashboard access; no public self-service registration endpoint is documented in the connection guide.
- Payout setup is optional to start work. Bounty currently lists India among supported Stripe Connect countries; payout is held until Stripe confirms the Operator's account. Any Stripe KYC or identity attestations remain owner-controlled.
- A secure browser connector has been suggested to finish the dashboard step and transfer the key directly into GitHub Actions Secrets without displaying it in chat. It is not yet connected. Do not ask the user to paste the raw API key into chat.


## Phase 5.1 — Complete source verdict reporting and latest green validation

- Fixed source verification reporting so 24-hour cached original-board verdicts are included in each report. Previously cached entries were skipped from the current report, making the full audit appear smaller than it was.
- The source verifier now returns cached and fresh results together, labels them CACHE or LIVE, refreshes incomplete source checks, and continues to refresh IssueHunt entries whose board funding state is not yet conclusively established.
- Added regression tests for cache visibility and expired-cache rechecks.
- Latest run 42952851852: SUCCESS, 93/93 tests; no Bounty API key, no active work; local CPU coder correctly skipped.
- Latest Jobbi run 42952851881: SUCCESS, 93/93 tests; 643 feed records, 324 index-level source-review candidates, 216 met source-verification filter. Full original-source audit:
  - 86 source issues locked
  - 36 existing attempts/PRs
  - 34 assigned
  - 37 closed
  - 12 stale IssueHunt funding
  - 5 stale unconfirmed funding
  - 2 payout withdrawn
  - 2 source restricted
  - 1 source URL is a PR
  - 1 source API 404/incomplete
  - 0 operator-gate candidates
- This is a verified rejection of stale/duplicate candidates, not a statement that no new opportunities can appear. Jobbi is re-indexed hourly; source feed refresh remains active.
- Credential bootstrap remains pending the authenticated Bounty dashboard. TinyFish has been suggested but is not yet connected. Once connected, use it to create the Agent in the owner dashboard and transfer the resulting key directly to GitHub Actions Secrets. Do not paste any key into chat.
