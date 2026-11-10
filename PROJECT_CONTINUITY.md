# PROJECT CONTINUITY — Nexus Autonomous Cloud Work Engine
**Canonical project:** `manish91082-coder/ai-content-system`  
**Primary branch:** `master`  
**Continuity version:** 1.0  
**Last updated:** 2026-11-11  
**Purpose:** Preserve the complete operating context so a new ChatGPT thread can resume without losing decisions, constraints, implementation status, or next actions.

---

## 1. Mission (locked)

Build a **zero-cost-first, cloud-hosted, highly autonomous AI Work-to-Earn Engine**. The system should discover legitimate paid work from AI companies, AI-training/data/research/coding/evaluation providers, and agent-native marketplaces; qualify opportunities; execute suitable work using AI agents; quality-check deliverables; submit through permitted interfaces; monitor acceptance; and reconcile actual payments.

The user's intended model is **AI performing paid assignments**, not seeking employment and not requiring the user to manually freelance each task.

### Economic success invariant
`REALIZED NET RECEIVED PAYMENTS - ALL ACTUAL COSTS > 0`

A listed reward, advertised rate, bid, accepted submission, escrow balance, or projected revenue is **not** realized income. Count revenue only when payment is actually received and reconciled.

## 2. User operating requirements (do not regress)

- User wants the assistant to lead and execute sequentially, make engineering decisions, research, build, test, audit, and maintain continuity.
- User explicitly said: **“Ye sab tum karo laptop pe mujhe kuch nahi karna”** and selected a **zero-cost cloud option**.
- Do not repeatedly ask the user to run terminal commands, install packages, edit files, or perform routine technical steps.
- Prefer actions the assistant can perform through connected GitHub tools and other available cloud connectors.
- The assistant cannot claim access to the user's physical laptop, PowerShell, WSL, private browser session, payment account, KYC, or wallet unless an authorized tool actually provides that access.
- Do not fabricate execution, test, account registration, API access, acceptance, or payment status.
- Only ask for user action when a genuine private-account authorization, KYC, legal consent, payment authorization, or other unavoidable human gate exists. Keep such requests minimal and specific.
- Prefer zero-cost and open-source technologies; no GPU; laptop must not be a required always-on worker.
- Hindi-first communication. English technical terms are acceptable.
- No employment/job offers as the solution. Focus on contract assignments, task marketplaces, AI training/evaluation/data work, research/coding deliverables, and enterprise data/AI partnerships.
- Do not spend funds, provision wallets, place bids, accept legal terms, or submit consequential deliverables without the required authorization and evidence.

## 3. Selected deployment strategy

**Cloud-first, GitHub Actions as the initial orchestration/scheduled execution layer.**

Why:
- No local laptop dependency for scheduled scans.
- Public GitHub repositories can use standard GitHub-hosted Actions runners at no charge, subject to current GitHub policy, quotas, and acceptable-use limits.
- Python standard library only for the first scanner.
- No API key or wallet is required for the read-only public scan.
- GitHub Actions schedules are best-effort, not guaranteed real-time. This is not an always-on server.

Do not assume free hosted CI can support unlimited continuous workloads. Keep scans short, low-frequency, bounded, and compliant. If scale exceeds free limits, reassess before incurring costs.

## 4. Marketplace strategy and research findings

### First pilot: MoltJobs
Official references:
- Public open jobs: https://moltjobs.io/open-jobs
- Agent registration: https://app.moltjobs.io/agents/new
- CLI docs: https://moltjobs.io/docs/cli
- CLI repository: https://github.com/Moltjobs/moltjobs-cli
- Docs/API repository: https://github.com/Moltjobs/docs
- Terms: https://moltjobs.io/terms
- API base: https://api.moltjobs.io/v1

Previously researched characteristics (must be re-verified against current official docs before relying on them):
- Public API, CLI, MCP and webhook workflows are described.
- 10 free bids/month and a 5% platform fee were stated in prior research; verify current terms.
- A listing does not prove escrow funding. Prefer only jobs whose funding/escrow state is verifiably confirmed.
- A bid or submission does not guarantee acceptance or payment.
- Account owner remains accountable for agent actions and legal compliance.
- API keys must never be placed in source code, chat, logs, public commits, or reports. Store only in a supported secrets manager after authorization.
- **Critical documentation discrepancy:** one official description referred to USDC escrow on Base, while CLI documentation described Turnkey-managed Polygon addresses holding USDC. This must be resolved with authoritative current documentation or platform support before any wallet provisioning, deposit, withdrawal, or payment-flow implementation. Do not assume either network is correct.

### Other candidate connectors
- Dealwork: https://api.dealwork.ai/ and https://api.dealwork.ai/skill.md
- Taskmarket: https://docs.taskmarket.dev/ and https://docs.taskmarket.dev/api/reference

Treat these as candidate sources only. Re-check current availability, API terms, funded status, India eligibility, payout route, fees, owner responsibility, and automation permissions before integration.

### Large AI companies / contributor platforms
Prior research distinguished enterprise data partnerships (e.g., OpenAI, Google, Scale AI) from open per-task APIs. Do not claim that OpenAI/Gemini/Claude model APIs are payment APIs; they are generally paid compute interfaces. Human contributor platforms may prohibit bots or require human judgment. Automate only where the platform explicitly permits agent execution and submission. Do not bypass human checks, KYC, access controls, or platform rules.

## 5. Current repository and implemented files

Repository: https://github.com/manish91082-coder/ai-content-system  
Branch: `master`

### Files added in this project phase
1. `cloud-work-engine/README.md`
2. `cloud-work-engine/scanner.py`
3. `.github/workflows/nexus-funded-job-scan.yml`
4. `cloud-work-engine/.gitignore`

The GitHub connector confirmed successful commits for these files:
- README commit: `f15f26cf9cdd87ef607f15a91d7544bdc9ea7a14`
- Scanner commit: `aa5ef98347e68ba658ac42b2b18008f193b396f3`
- Workflow commit: `13e8762cfb787e9136ed082da65b191c37b76ce4`
- .gitignore commit: `204d56fdb582400aa430b86096bfb626f7f7dd6f`

Workflow file was fetched back from GitHub and its content verified. The workflow configuration:
- Workflow name: `Nexus funded job scan`
- Manual trigger: `workflow_dispatch`
- Schedule: cron `17 * * * *` (hourly at minute 17)
- Runner: `ubuntu-latest`
- Runs `python cloud-work-engine/scanner.py`
- Uploads `report/` as a 7-day artifact
- Uses read-only repository permissions.

### Scanner behavior
- Calls public MoltJobs API at `https://api.moltjobs.io/v1/jobs`
- Query parameters: `status=OPEN&funded=true&limit=100`
- Uses Python standard library only.
- Includes bounded retry handling and a maximum 20-page pagination safety cap.
- Stores raw API pages and normalized count in a timestamped JSON report.
- Does not authenticate, register, bid, claim, execute, submit, access wallets, or transfer money.
- Reports zero funded jobs as a valid result rather than pretending work exists.

### Verification status — important
- GitHub file creation commits succeeded.
- Workflow file was fetched from GitHub and verified.
- A read of repository Actions history did not find a run for `nexus-funded-job-scan.yml` at that time.
- **No successful live workflow execution has yet been evidenced.**
- **No live API response from the new scanner has yet been captured.**
- **No agent account registration, bidding, task execution, acceptance, or payment has occurred in this phase.**
- Do not describe the scanner as running successfully until a workflow run and artifact/log are inspected.

## 6. Safety, compliance, and execution gates

Before enabling authenticated or write-capable operations, verify all of the following:
1. Platform permits autonomous agent use for the specific task category.
2. Task is genuinely funded/escrowed, not merely advertised.
3. Acceptance criteria and review/dispute windows are clear.
4. Owner identity, account ownership, KYC, tax, and country eligibility are understood.
5. Payout rail, chain, token, withdrawal route, and India availability are verified.
6. Fees, network costs, model costs, and possible non-payment risks are quantified.
7. Task can be completed without prohibited scraping, deception, impersonation, privacy violation, or bypassing platform controls.
8. Human approval is retained for legal agreements, identity verification, financial transfers, and irreversible submissions when required.

Never invent identities, fake human participation, evade platform anti-bot rules, or misrepresent AI-generated work as human work where disclosure is required.

## 7. Required architecture (target, not yet implemented)

```text
Cloud Scheduler / GitHub Actions
        |
Marketplace Connectors (MoltJobs, Dealwork, Taskmarket, others)
        |
Opportunity Normalizer + Evidence Store
        |
Eligibility / Funding / Risk / ROI Gate
        |
Task Planner + Capability Router
        |
AI Execution Agents (only permitted task types)
        |
Independent QA / Tests / Evidence Pack
        |
Human approval gate where required
        |
Authorized submission adapter
        |
Acceptance / dispute / payout monitor
        |
Payment ledger: received funds - all costs
```

Design principles:
- Read-only discovery first; write-capable connectors only after verification.
- Idempotency keys and duplicate prevention.
- Rate limits, bounded retries, timeouts, audit logs, and cost ceilings.
- Per-task sandboxing; no arbitrary untrusted task instructions executed on host.
- Treat marketplace content as untrusted input; defend against prompt injection and data exfiltration.
- Separate model/provider API credentials from marketplace credentials.
- Never give an agent unrestricted wallet signing or withdrawal authority.
- Evidence provenance: retain source URL, timestamp, raw response, task ID, funding evidence, acceptance proof, transaction hash, and actual received amount.
- No paid model API or paid infrastructure unless net-positive economics are demonstrated and explicitly authorized.

## 8. Immediate next actions — strict sequence

### Phase 1A — Prove cloud execution
1. Inspect GitHub Actions workflows for `ai-content-system`.
2. Confirm the new workflow is recognized by GitHub.
3. Trigger a manual run only if the connected GitHub tooling exposes a supported dispatch action; otherwise use the scheduled run.
4. Fetch workflow run status, job steps/logs, and artifact.
5. If the workflow is not recognized or fails, diagnose and patch through GitHub connector. Do not ask the user to use a terminal.

### Phase 1B — Prove API schema
1. Call the public MoltJobs jobs endpoint using an available safe read-only HTTP capability.
2. Inspect exact response schema, pagination, funded status, status enums, and error behavior.
3. Compare live API output with scanner assumptions.
4. Correct parser and add unit tests for known schema variants.
5. Run the scanner in cloud and retain first report.
6. If the endpoint/API schema is unavailable, document the precise blocker and test official documented alternative; do not guess endpoints or fields.

### Phase 1C — Multi-marketplace discovery
1. Research Dealwork and Taskmarket current API schemas and terms.
2. Implement read-only adapters separately.
3. Normalize opportunities to a common schema.
4. Compare verified funded opportunities across marketplaces.

### Phase 2 — Execution design
1. Build task-type capability registry.
2. Add local/cloud sandbox execution for safe task categories.
3. Add quality gates and evidence generation.
4. Keep all external writes disabled until eligibility, terms, and authorization are verified.

### Phase 3 — Controlled earning pilot
1. Complete only one small, fully funded, low-risk task.
2. Require explicit acceptance conditions and capped costs.
3. Submit through a permitted workflow.
4. Track acceptance and settlement.
5. Count revenue only when received and reconciled.
6. Expand only after one end-to-end payment is evidenced.

## 9. Continuity protocol for the next ChatGPT thread

When a new chat starts, the user can say:

**“Nexus Autonomous Cloud Work Engine project resume karo. GitHub repository ki PROJECT_CONTINUITY.md file read karo aur last verified checkpoint se bina repeat kiye continue karo.”**

The assistant must then:
1. Read this file from the repository before asking the user to repeat context.
2. Inspect actual current repository state and latest GitHub Actions status.
3. Verify which steps have happened since this file was last updated.
4. Update this file after each material milestone, decision, blocker, or implementation change.
5. Preserve all locked requirements and do not silently change the mission.
6. Never infer success from code being committed; inspect execution evidence.
7. Continue with the next unfinished action, not restart the project.

## 10. Change log

- **2026-11-11:** User reaffirmed zero-cost cloud option and asked assistant to perform work without requiring laptop-side setup.
- **2026-11-11:** Added first read-only MoltJobs funded-job scanner and hourly GitHub Actions workflow to `ai-content-system` on `master`.
- **2026-11-11:** Verified GitHub commits and fetched workflow file. First successful scheduled/manual workflow run remains unverified.
- **2026-11-11:** This continuity constitution created to preserve project state across chat-thread limits.

---
**Non-negotiable status rule:** distinguish *planned*, *committed*, *configured*, *executed*, *verified*, *accepted*, and *paid*. Never collapse these into one status.


## 11. Continuation update — 2026-11-11 (Phase 1A/1B)

### Official MoltJobs API schema verified
- Retrieved the official MoltJobs documentation repository's machine-readable OpenAPI spec from: https://raw.githubusercontent.com/Moltjobs/docs/main/openapi.json
- Confirmed `GET /v1/jobs` is the public open-jobs endpoint.
- Confirmed query parameters include `cursor`, `limit` (1–100), `status`, `vertical`, `templateId`, `funded` (boolean), `agentId`, and `posterId`.
- Confirmed `funded=true` is explicitly described as filtering jobs whose escrow has been deposited. This supports the scanner's funded filter, but does not independently verify the live service's returned records.
- Official docs describe a response envelope with a `data` property; list endpoints return arrays under `data`. Source: https://github.com/Moltjobs/docs
- The direct API endpoint was not successfully queried in this execution environment; do not claim a live result.

### Parser hardening and tests added
- Updated `cloud-work-engine/scanner.py` to accept documented `{data:[...]}` envelopes and several common cursor metadata layouts.
- Added `cloud-work-engine/tests/test_scanner.py` with 5 unit tests for documented envelope, root cursor, nested data cursor, legacy jobs array, and invalid payload handling.
- Updated GitHub Actions workflow to run unit tests before the scanner.
- Added a path-filtered `push` trigger to run validation after relevant project changes, while retaining manual dispatch and hourly schedule.
- Commits: scanner `7ba05d03b6629887f1426063ad1aa9d86115fb30`; tests `039c5c96f6122241d96c1d925ea931977a5866d7`; test import fix `35843e71bed0a151723f069f4fd7bb96847c4e51`; workflow test step `99234a36db72c32574c3d00ababce18dd39ea833`; push trigger `0dd8d707b1d1616f3accff0870c3138190a8fdf8`.

### Current verified execution state
- Files/commits exist in GitHub and can be fetched back.
- Latest Actions history query returned 197 total runs but zero runs whose workflow path matches `.github/workflows/nexus-funded-job-scan.yml`.
- Therefore workflow execution is still **NOT VERIFIED**. The GitHub connector available in this session exposes Actions read operations but no workflow-dispatch write operation. A dispatch requires Actions:write permission according to GitHub's official REST docs: https://docs.github.com/en/rest/actions/workflows# create-a-workflow-dispatch-event (remove the space before fragment when using URL).
- Possible causes to investigate: workflow not yet indexed/recognized, Actions disabled/restricted in repo settings, schedule not yet fired, or the connector's run listing cache/coverage. Do not assume a cause without evidence.

### Next action, in order
1. Re-query GitHub Actions runs after the latest commit and look specifically for the workflow path.
2. If still absent, inspect repository Actions settings/workflow visibility using available read APIs; do not ask user to run terminal commands.
3. If Actions are disabled or the connector lacks write permission, choose another genuinely zero-cost cloud executor with an assistant-accessible deployment/control path. Do not claim deployment is live merely because YAML exists.
4. Once cloud execution is proven, inspect logs/artifact and correct any API/parser errors.
5. Keep MoltJobs write operations disabled until agent account authorization, task-specific automation permission, funding, settlement rail, and payment route are verified.


## 12. Verified cloud run + marketplace expansion audit — 2026-11-11

### First cloud execution is now VERIFIED
- GitHub Actions run: https://github.com/manish91082-coder/ai-content-system/actions/runs/42893727598
- Run ID: `42893727598`; conclusion: `success`.
- Steps verified successful: checkout, scanner unit tests, read-only scanner, artifact upload.
- Artifact ID: `13800205921`; artifact name `nexus-funded-jobs-42893727598`; report timestamp `2026-11-10T20:17:01Z`.
- Report contained 10 open funded listings.
- All 10 were `purpose=PLATFORM_REFERRAL`, `participationMode=AUTOMATIC_FORUM_REWARD`, each with `budgetUsdc=0.2`, titles like “Referral bounty — bring an agent that posts on the forum”. These are not ordinary paid work assignments and require referral/new-owner conditions. Do not pursue them as the user's work-to-earn path.

### Candidate filter implemented and verified
- Scanner now classifies funded listings and excludes platform referral/forum reward campaigns from the ordinary paid-task candidate pool.
- Added tests for referral exclusion and normal task pass-through to next-stage review.
- A subsequent Actions run ID `42893846494` completed with conclusion `success`; unit tests, scanner, and artifact upload all passed.
- Artifact ID `13799612084`; report timestamp `2026-11-10T20:17:43Z`.
- Report metrics: `funded_open_jobs_count=10`, `eligible_task_candidates_count=0`, `excluded_by_policy_count=10`.
- This is the first meaningful verified marketplace finding: **MoltJobs currently returned no ordinary funded task candidates in this scan**, despite 10 funded open listings. No bid, claim, work, submission, wallet action, or payment occurred.

### Dealwork current official skill audit
- Current skill file: https://api.dealwork.ai/skill.md (version 1.6.5 at research time).
- API base: `https://api.dealwork.ai/api/v1`.
- Browse jobs: `GET /api/v1/jobs?per_page=20&sort=newest`; docs say poll no more than once every few minutes and respect 429 Retry-After.
- Agent quick onboarding may be performed via `POST /api/v1/agents/onboard` with `autonomous=true`, but the Terms still make a responsible human/legal-entity owner fully accountable for agent bids, deliveries, spending, and conduct. Do not register or accept terms without required authorization.
- Account credentials include API key and HMAC secret, shown once. Keep them in a secret store, never logs/repo/chat.
- Fees shown in current public docs: 10% standard contracts; 3% AI-to-AI. Terms dated 2026-07-15. On-chain top-ups/payouts use USDC on Polygon; fiat payout methods are shown in account wallet, not guaranteed for India.
- Current docs explicitly require never starting work before escrow locks; buyer review can auto-approve after 24 hours. Must build this into the risk/acceptance logic.
- Public image arena is free but has no prize/escrow; it is reputation, not revenue. Do not count as earnings.

### Taskmarket current official API audit
- API docs: https://docs.taskmarket.dev/api/reference; developer overview: https://docs.taskmarket.dev/developer/overview; live public board: https://api.taskmarket.dev/.
- Production API base: `https://api.taskmarket.dev`; REST endpoints under `/api`.
- Public task discovery: `GET /api/tasks`, supports status, phase, mode, requester actor type, tags, min/max reward, deadline, sort, limit, cursor. Response includes tasks, hasMore, nextCursor.
- Task modes include bounty, claim, pitch, benchmark, auction.
- Network/token: Base chain 8453 with USDC; Tempo chain 4217 with OUSD. No default chain; network must be explicit.
- Some write operations require wallet signatures and x402/MPP payment. Pitch and service actions may incur protocol charges. Do not attempt claims, pitches, submissions, or payment actions until an authorized wallet and cost policy exist.
- Public live homepage search result showed open examples at 15 USDC, 100 OUSD, 2.5 USDC, and 0.05 OUSD; these are listing examples only and not yet individually verified for eligibility/funding or India payout.

### Immediate next engineering sequence
1. Extend the GitHub Actions read-only scanner with separate Dealwork and Taskmarket adapters, no credentials and no writes.
2. Use Dealwork docs to query open jobs; validate whether public GET requires auth and how funded/escrow status is represented. Filter human-only work and AI-disallowed work.
3. Use Taskmarket `GET /api/tasks?status=open&limit=...` to discover public tasks; capture reward units, mode, expiry, escrow state, chain, and requester/worker actor type. Never pay x402/MPP in read-only discovery.
4. Normalize all marketplace results into a common opportunity schema with provenance and policy exclusions.
5. Add economic qualification: fees, expected model/compute costs, task effort, settlement and withdrawal path, acceptance risk, and minimum net payout. No fabricated cost estimates.
6. Update continuity after every significant implementation/run.

### Important verified state correction
- Earlier continuity sections said the first run was unverified. This section supersedes that status: the GitHub Actions cloud workflow has now run successfully twice and artifacts were downloaded and inspected. Keep the old history for audit, but use this latest section as current state.


## 13. Multi-marketplace discovery — live cloud verification (2026-11-11)

### Implemented
- Replaced the single-source scanner with three public read-only adapters: MoltJobs, Dealwork, and Taskmarket.
- Added a common opportunity schema with platform/task ID, title/description, reward amount, raw Taskmarket base units, currency, chain, funding evidence state, actor type, task mode, deadline, tags, acceptance criteria, source URL, fetched timestamp, raw record, and policy decision.
- Taskmarket reward conversion uses Decimal and six-decimal base units; raw amount is retained.
- Added explicit UNKNOWN / BLOCKED / REVIEW_REQUIRED classifications. An escrow transaction hash is not treated as independently verified on-chain proof.
- Added tests for envelopes, six-decimal conversion, Taskmarket escrow evidence gate, MoltJobs referral exclusion, and Dealwork unfunded gate.
- All writes remain disabled.

### Verified Actions runs
- Initial multi-marketplace run 42894201962 succeeded; artifact showed all three public APIs responded, but Dealwork status/funding classifier was still being corrected.
- A classifier test initially failed in run 42894338073; logs identified a stale expectation in the Dealwork test. It was corrected.
- Final verified run: 42894478350, conclusion SUCCESS.
  - Job: 130103840159; checkout, unit tests, scanner, and artifact upload all succeeded.
  - Artifact ID: 13798679626; name: nexus-funded-jobs-42894478350.
  - Artifact report timestamp: 2026-11-10T20:20:42Z.
- Final report totals: 35 public listings discovered: MoltJobs 10, Dealwork 20, Taskmarket 5.
  - MoltJobs: 10/10 excluded as platform referral/forum reward campaigns.
  - Dealwork: 20/20 blocked; live records report posterFunded=false, with claimBlockedReason values including underfunded and poster_unfunded. Listed USD budgets are not funded work.
  - Taskmarket: 5/5 open tasks have an escrowTxHash reference and remain REVIEW_REQUIRED. The hash has not yet been independently checked on-chain, and task terms/AI permissions/payout remain unverified.
- Economic gate remains NOT_EVALUATED; no task execution, submission, acceptance, or payment occurred.

### Current next action
1. Enrich the five Taskmarket opportunities with canonical GET /api/tasks/{taskId} details and GET /api/tasks/{taskId}/terms (public read-only only).
2. Verify chain-specific transaction receipts for Base (8453) and Tempo (4217) using authoritative explorers/RPC evidence; do not equate a nonempty hash with confirmed escrow.
3. Inspect full task requirements, expiry, acceptance/review windows, worker type, stake, rejection fee, and settlement costs.
4. Determine which tasks are genuinely executable by an autonomous AI without external purchases, paid protocol actions, or human-only activity.
5. Only then calculate conservative net payout and select one small pilot. No wallet actions or write operations until explicit authorization and all gates pass.

### Live marketplace evidence from the final artifact
- Dealwork public list returned 20 records with page 1, per_page 20, total 138; all 20 records in the returned sample had posterFunded=false.
- Taskmarket public list returned 5 tasks with hasMore=false; reward values included 1 OUSD, 1 USDC, 15 USDC, 100 OUSD, and 10 OUSD. These are listed rewards, not earned revenue.
- The five Taskmarket task modes were all bounty; expiry times are retained in the artifact. One listed task had a deadline earlier than the scan timestamp, so expiry must be rechecked before any further consideration.


## 14. Taskmarket detail, terms and escrow receipt verification — 2026-11-11

### Canonical details and settlement terms
- Added bounded public read-only GET /api/tasks/{taskId} and GET /api/tasks/{taskId}/terms enrichment for up to 10 newest Taskmarket tasks.
- Added chain-aware JSON-RPC eth_getTransactionReceipt checks: Base Mainnet via https://mainnet.base.org and Tempo Mainnet via https://rpc.tempo.xyz.
- The verifier checks successful receipt status and ERC-20/TIP-20 Transfer logs from the documented settlement token to the correct Taskmarket Diamond. It compares total matching transfer amount with the task's listed reward. No transaction was sent.
- Final verified cloud run: `42895409119`, conclusion `success`; job `130107123390`; unit tests, read-only scanner and artifact upload succeeded.
- Artifact ID `13800032456`, name `nexus-funded-jobs-42895409119`; report timestamp `2026-11-10T20:27:14.299208+00:00`.
- All five Taskmarket details and terms reads succeeded; all five transaction receipts were successful, and each had a token transfer to the chain-correct Taskmarket Diamond equal to the listed reward. This is evidence of escrow deposit, not a guarantee of worker award or payout.

### Five Taskmarket opportunities reviewed
1. `TSK-6RW06814` — 1 OUSD, Tempo, economics article, deadline 2026-11-11 07:59:04Z (13:29:04 IST). 42 submissions, zero awards at scan time. No stake; standard terms; reject fee amount 0.2 OUSD; decision deadline 2026-11-18 07:59:04Z. A draft article was prepared and committed at `cloud-work-engine/deliverables/taskmarket/TSK-6RW06814-parallel-fx-rates.md` (commit `22e2feeb1960dc89bc91f25c80e04a8ba4e60855`). Draft body is within the requested 800–1,500 word range. Not submitted. Taskmarket docs state first five bounty/benchmark submissions per task are free, then later submissions cost 0.001 token; with 42 submissions already recorded, a new submission is not zero-cost. No authorized/funded worker wallet exists.
2. `TSK-J1WYKT0H` — 1 USDC, Base, FlapJax on-chain treasury audit. Requires first-timer status, a new worker wallet and handle, a public audit page, BSC wallet binding, and pays 100,000 FLAPJAX off-platform (the USDC listing deposit is not the worker payout). Exclude: identity/wallet requirements, off-platform token payout, and sybil/account-age rules.
3. `TSK-836Z6Q65` — 15 USDC, Base, Lumen House shopping challenge. Requires buying several products/NFT and a pass, entrants bear purchase/network costs, no guaranteed prize, and the Help Map is limited to eligible U.S. purchasers. Exclude: requires spending and uncertain prize.
4. `TSK-E4J7K6WE` — 100 OUSD, Tempo, 15-second Frontier cinematic. Three winners split 50/30/20 OUSD; requires a commercially licensable video-model workflow, source ZIP and process file; 93 submissions at scan time. Exclude from zero-cost pilot until a compliant free video-generation pipeline and time budget are proven.
5. `TSK-JKVSTHB7` — 10 OUSD multiplayer strategy game; deadline 2026-11-10 21:16:20Z, deadline 2026-11-10 21:16:20Z (2026-11-11 02:46:20 IST). At the 01:57 IST scan it had about 49 minutes remaining; it was not selected because a secure build, test and public deployment within that window was not realistic. Re-check current status before any reuse.

### Research deliverable status
- Created a source-backed economics article draft for the 1 OUSD bounty, citing IMF research and country reports on Egypt, Nigeria and Ethiopia. It is committed in the repository but has NOT been submitted to Taskmarket.
- Reason: existing 42 submissions imply the first-five free submission allowance is exhausted; later submissions cost 0.001 OUSD, and no user-authorized/funded wallet or Taskmarket account is available. Do not pay or submit without explicit authorization.

### Official documentation sources consulted
- Taskmarket API reference: https://docs.taskmarket.dev/api/reference (task details, task terms, bounty submission fee schedule).
- Taskmarket raw REST fallback: https://docs.taskmarket.dev/reference/raw-api (canonical detail and terms routes).
- Taskmarket network reference: https://docs.taskmarket.dev/reference/network (chain IDs, tokens and explorers).
- Taskmarket Base reference: https://docs.taskmarket.dev/reference/base (Base RPC, Taskmarket Diamond, USDC).
- Taskmarket Tempo reference: https://docs.taskmarket.dev/reference/tempo (Tempo RPC, Taskmarket Diamond, OUSD).

### Next actions
1. Re-fetch the Taskmarket open list and the economics task detail immediately before considering any action; deadlines and submission counts change.
2. Do not submit the article unless the user authorizes the 0.001 OUSD submission cost and the account/wallet authorization gate is resolved.
3. Expand discovery beyond the three agent marketplaces toward legitimate no-cost AI contributor/task platforms with public task discovery and permitted automation. Screen for India eligibility, AI execution permission, no upfront purchases, verifiable payout, and positive net economics.
4. Keep all writes, wallet operations, registrations and paid submissions disabled until each platform's owner-consent and financial authorization gates are met.


### Latest refreshed scan — 2026-11-11 02:00 IST
- Run `42895597762` completed successfully; job `130107788654` passed checkout, tests, scanner and artifact upload. Artifact ID `13798589771`, name `nexus-funded-jobs-42895597762`; report timestamp `2026-11-10T20:28:24.670174Z`.
- Marketplace counts unchanged: MoltJobs 10, Dealwork 20, Taskmarket 5. All five Taskmarket tasks remain `open` in the fresh response; all five receipts still return successful status and matching token transfer to the correct Taskmarket Diamond. The game bounty deadline is 2026-11-10 21:16:20Z (02:46:20 IST), so at this scan it still had about 48 minutes; not selected due the infeasible secure build/test/deploy window.
- The 1 OUSD article task still had 42 submissions, zero awards, and deadline 2026-11-11 07:59:04Z (13:29:04 IST). The research draft is prepared but unsubmitted. No wallet or payment authority is available; later bounty submissions incur the documented 0.001 OUSD fee after the first five submissions.


## 15. Agent-native marketplace expansion — 2026-11-11

- Four new candidates researched: BasedAgents, Verdikta Bounties, Artisan, BotBounty.
- BasedAgents explicitly supports autonomous agents and public task discovery, but bounty claims require a 1 USDC bonded slot and wallet proof; free tasks earn reputation only. Paid path blocked under zero-capital constraint.
- Verdikta accepts AI agents and escrows ETH. Current public feed showed only two open advanced mathematics proof bounties (#387 and #386), each 0.032 ETH with a 95% threshold. Submission costs approx. 0.00024 ETH oracle prepay plus gas. Both excluded for capability/cost risk.
- Artisan uses Orbio CREDIT for inference and charges 5% on accepted work; zero-cost inference and India withdrawal are unverified. Deferred.
- BotBounty homepage claims AI-agent bounties, but public skill/API could not be inspected and homepage minimum-bounty statements conflict ($10 vs $1). Unverified; do not integrate.
- Human contributor platforms are excluded where work requires human judgment or prohibits external LLMs; Handshake AI explicitly prohibits LLM use absent written authorization.
- No registrations, keys, wallets, deposits, claims, submissions, or spending occurred.
- Detailed audit: cloud-work-engine/research/agent-native-marketplace-expansion-2026-11-11.md
- Next: validate BasedAgents public GET schema and Verdikta feed schema, then add read-only adapters only. Keep all write operations absent.


## 16. BasedAgents live adapter — first verified cloud scan (2026-11-11)

### Implementation
- Added public read-only adapter in `cloud-work-engine/scanner.py` for `GET https://api.basedagents.ai/v1/tasks?status=open&limit=100&offset=0`.
- Normalizes task ID, title, description, bounty, token/network, creator type, expiry, escrow and claimability.
- Added unit tests for funded bounty bond gate, free reputation-only task exclusion, and unready escrow.
- The scanner has no BasedAgents registration, claim, deliver, wallet, signature, or payment code.
- First implementation commit: `ae873e58a684177925ac17b23ac79ad7d0496791`; tests commit: `40ce23e042cc012ab78df8a1f2693a35fc738c3e`.
- Follow-up classification commit distinguishes sign-at-accept bounty (not prefunded) from actual escrow: scanner `061385bf60862490e2774151fb4e28580e2a02c2`; tests `57c38bbe1683913ea2f9ea26b215d9f432e0b465`.

### First live result
- GitHub Actions run `42896368586`: https://github.com/manish91082-coder/ai-content-system/actions/runs/42896368586
- Run completed successfully. Unit tests and scanner succeeded; artifact `nexus-funded-jobs-42896368586`, ID `13799399561`.
- The live scanner queried all four sources: MoltJobs 10, Dealwork 20, Taskmarket 5, BasedAgents 16; total 51 listings.
- BasedAgents 16 records: 6 free/no-cash tasks, excluded from revenue; 10 bounty tasks, all are sign-at-accept with no escrow object and payment_status=pending, therefore not prefunded/guaranteed. The initial classifier labeled them generic escrow-not-ready; follow-up patch now identifies the exact sign-at-accept risk.
- The 10 paid-looking tasks are clustered around one poster, Industrial Platform / Sentinel. Five list 0.25 USDC but require genuine external installation plus at least 0.50 USDC of settled Industrial Platform revenue across two UTC days and a second-day paid cycle. Five list 2.00 USDC cashback but require at least 2.50 USDC of settled revenue across two UTC days and a second-day paid call. This requires an existing authorized external runtime, wallet/payer setup and generating paid usage; it is not a zero-cost, self-contained assignment. Exclude from pilot.
- One free BasedAgents task asks for a multi-day full self-host stack kit and public delivery. It is not paid, takes several focused days and has a seven-day claim window; do not claim for revenue objective.
- Artifact was downloaded and inspected locally. No account, agent key, wallet, bond, claim or delivery was created.

### Current workflow verification
- Run `42896513388` was triggered by the follow-up classifier/test commit. At the last status check it was in progress. Do not mark this follow-up run successful until its final conclusion is fetched.

### Decision
- BasedAgents adapter is implemented and its first live execution is verified. Current sample has zero suitable tasks for the user's zero-upfront-cost/no-external-installation constraints.
- Continue hourly read-only monitoring. If BasedAgents later exposes funded, claimable, genuinely escrow-backed tasks, they remain blocked until a wallet and 1 USDC per-slot bond are explicitly authorized. Sign-at-accept tasks remain blocked as non-prefunded.
- Next: inspect current run `42896513388` to verify the classifier patch, then validate Verdikta task detail/on-chain status and BotBounty canonical API before adding either adapter.


### Follow-up test correction — 2026-11-11
- The scanner-classifier patch run `42896513388` completed successfully, including tests and scanner execution.
- A subsequent test-only commit initially had a mistaken assertion: the unready-escrow test expected the sign-at-accept reason. Run `42896520728` and the later docs-triggered run `42896574541` failed on that test expectation, not on scanner runtime.
- Corrected the test by restoring the escrow expectation and adding a separate test for `escrow: null` / `payment_status: pending` sign-at-accept bounty. Test commit: `710caa7bb72776a8cd25080e762658f181396db6`.
- New validation run `42896620155` was queued at the latest check; fetch its final conclusion before calling the test correction verified.
- Important live-feed result: BasedAgents has 16 open tasks, 6 free and 10 paid-looking. The 10 paid-looking entries are sign-at-accept, not escrow-funded, and all tied to Industrial Platform/Sentinel external-runtime revenue-generation prerequisites. None qualifies as a zero-upfront-cost independent assignment.


## 17. Bounty (trybounty.ai) adapter and candidate audit — 2026-11-11
- New candidate audit identifies Bounty as the strongest zero-capital paid-work lead so far: no agent deposit, subscription, API access fee or separate payout fee; India is on its Stripe Connect payout country list subject to Stripe approval. Payout onboarding/KYC remains an operator-controlled requirement; funds can be held until payout account is ready.
- API discovery is authenticated: `GET https://api.trybounty.ai/v1/agent/bounties?status=open` with `Authorization: Bearer <Agent API key>`. Creating the key requires dashboard access and an Agent Card. No account/key exists in the project environment.
- Added dormant read-only Bounty adapter in `cloud-work-engine/scanner.py`. If `BOUNTY_AGENT_API_KEY` is absent, it returns a `needs_agent_api_key` status without calling the API. If present, it only reads open bounty list. No bid/claim/message/submit routes exist in the adapter. Payout cents are normalized to currency units.
- Added unit tests for Bounty bid-flow unknown payout and closed-task exclusion. Commits: scanner `2168ea235a4cf743f989c4c5d91a6c61b3d1b71c`; tests `5fa71103bf60e6f9a91657ba9f3e14874cb094c4`; cents normalization commit follows.
- TryBounty supports claim (fixed funded payout) and bid (owner accepts one offer). In bid flow, payout_cents is null until acceptance; never count budget as earned revenue. India Stripe Connect is supported subject to approval; non-US payouts may still be unavailable. Buyer review is 72 hours after verification. Operator remains responsible for agent output and IP transfers on settlement.
- BotBounty remains unverified: homepage API URL and skill.md API base differ; API feed inaccessible in research pass. Excluded pending canonical endpoint and escrow evidence.
- Verdikta current feed still has only two highly specialist math bounties (#387, #386), 0.032 ETH each at 95% threshold; each evaluation requires approx. 0.00024 ETH prepay plus gas. No wallet signing/spend.
- Last known validation run `42896620155` was queued; verify final status. New Bounty adapter commits will trigger a fresh Actions run. No marketplace credentials, KYC, bids, claims, submissions or payouts were created.


## 18. Bounty API semantics and cloud verification — 2026-11-11
- Latest full scanner run `42896912642` completed SUCCESS; unit tests, all scanner steps and artifact upload passed. Artifact `13800832283` was downloaded and inspected.
- Report: 51 listings across four active public sources. Bounty source status is `needs_agent_api_key`, zero rows, writes false. This is not evidence of zero Bounty tasks. Economic gate remains `NOT_EVALUATED`.
- Current Bounty raw API docs confirm production base `https://api.trybounty.ai`, bearer Agent API key, `GET /v1/agent/bounties?status=open`, and mandatory full pagination via `has_more` and `next_cursor`. Polling recommendation is 30 seconds; GitHub Actions cron is not a suitable 30-second event loop, so do not claim the current hourly monitor meets that cadence.
- Important payout correction: new Bounties use `flow=bid`. Their `payout_cents` is null until owner accepts an agent bid. `budget_cents` is a guide only, not guaranteed income. Older `flow=claim` Bounties have fixed owner-funded payout. Never classify a bid budget as escrow or earned payout.
- API supports details, events, messages, bids, claims, attachments and submissions, but those write endpoints remain out of scope until separately authorized. Listing task availability does not hire the Agent. Operator responsibility for work output remains with the account owner.
- Docs also say Agent dashboard and Agent Card are required; API key is privileged and must remain in server-side secret storage. Stripe Connect payout setup can be completed later; India appears on supported-country list, subject to Stripe approval. Earnings are held until payout setup is approved.
- Fresh source: https://docs.trybounty.ai/agents/connect/ ; https://docs.trybounty.ai/agents/raw-interface/ ; https://docs.trybounty.ai/agents/how-it-works/ ; https://docs.trybounty.ai/agents/sdk/ .
- Next engineering gate: add cursor-complete pagination and separate `budget_cents` from `payout_cents`; add tests for bid-vs-claim semantics and duplicate-safe paging. Keep authenticated API adapter dormant until user creates Agent and places API key in GitHub Actions secret store.


## 19. Phase 3 — Autonomous Bounty discovery and hired-work preparation — 2026-11-11

### What is implemented
- Added cloud-work-engine/bounty_agent.py: bearer-authenticated, read-only Bounty client with complete next_cursor pagination, repeated-cursor protection, ID deduplication, per-Bounty detail reads, payout/budget normalization, and active-work lookup (claimed,submitted,reviewing,disputed).
- Added durable Bounty version tracking in .nexus_state/bounty_versions.json. New, changed and unchanged Bounty versions are classified; GitHub Actions cache restores/saves state across scheduled runs.
- Added cloud-work-engine/task_triage.py: deterministic allowed-skill and risk triage. Test Bounties and unsupported/high-risk tasks are excluded; paid candidates require subsequent economics/verification review.
- Added cloud-work-engine/model_gateway.py: OpenRouter openrouter/free only, with no paid model fallback. It refuses to send an inference request if the API key is missing and treats rate-limit/funding errors as unavailable free capacity.
- Added cloud-work-engine/draft_executor.py: only processes work which is already hired (status=claimed, claim_status=active), excludes test Bounties, skips detail failures and attachments pending safe ingestion, and generates local Markdown drafts. Every draft is marked NOT SUBMITTED. Local QA checks substance and non-claims. Draft version deduplication is persisted.
- Added dedicated .github/workflows/nexus-bounty-agent.yml with five-minute best-effort polling, tests, read-only discovery, triage, free-model readiness, hired-work draft preparation, state cache and 14-day report artifacts.
- Updated primary scanner to use the same canonical Bounty pagination/details adapter and fixed the API's _id, payout_cents, budget_cents, flow, and test-Bounty semantics. Primary scanner workflow passes Bounty API key through GitHub Secrets.
- Tests cover pagination/deduplication, detail enrichment, Bounty fixed payout vs bid budget, test Bounty exclusion, active claim gating, attachment dependency and no-key/no-paid-fallback behavior.

### Cloud validation and current gate
- Dedicated Bounty workflow 42898672894 succeeded: 27 tests passed; all steps completed. Artifact showed no Bounty API key configured, no authenticated tasks discovered, no draft created, and no marketplace writes.
- Subsequent primary scanner test run exposed a stale expected reason string in one legacy regression test. The classifier was corrected to preserve the bid_flow prefix; the newest runs must be fetched before this checkpoint is marked fully green.
- New workflow is a five-minute GitHub Actions schedule, not a 30-second event loop. It is best-effort and may be delayed by GitHub scheduling.
- Required cloud Secrets (never paste into chat or source): BOUNTY_AGENT_API_KEY, OPENROUTER_API_KEY. Both are optional; missing keys produce a clean idle state.
- OpenRouter free model route openrouter/free is the only selected route; no paid model fallback is allowed. The free tier is currently capped at 50 requests/day, subject to model/provider limits.
- No accounts, API keys, Stripe payout setup, KYC, bids, claims, messages, submissions or payments were created. No income is claimed.

### Execution policy
- Keep discovery and draft preparation automatic.
- Do not automatically bid/claim, message owners, or submit work until the account is configured and action authority is explicitly resolved. Accepted work is the only input to the draft executor.
- Do not process customer-private attachments until safe file ingestion and content extraction are implemented.
- Never label model-generated drafts as delivered, accepted or paid.

## 20. BountyBoard discovery and marketplace filtering — 2026-11-11

- Added cloud-work-engine/bountyboard_public.py: anonymous read-only GET discovery from https://www.bountyboard.work/api/bounties?status=OPEN&limit=50; cursor pagination, ID deduplication, normalized gross reward, estimated 90% worker share, explicit agent eligibility and machine-readable escrow fields.
- Added cloud-work-engine/tests/test_bountyboard_public.py covering API envelopes, net amount, no assumed escrow, academic-integrity exclusion, physical-presence exclusion and short-page cursor continuation.
- Added BountyBoard adapter and test paths to the Nexus Bounty five-minute workflow. No account, agent key, Stripe account, bid, claim or submission was created.
- Official homepage currently shows 6 open bounties and 86 members; visible tasks consist largely of location-specific iPhone/photo collection, plus one $1 writing-schoolwork task. The local/physical tasks are excluded for autonomous cloud execution; schoolwork is excluded for academic integrity. No current candidate is promoted to work.
- BountyBoard pricing: 10% fee only after approved delivery; USD/EUR/PLN/CZK/HUF; Stripe Express onboarding. India payout eligibility for this platform has not been independently established. Terms last updated 2026-07-17 and include a pending legal-jurisdiction placeholder.
- AgentMesh was rejected as revenue source: official pricing page states its credits are in-platform units, non-crypto, non-withdrawable and the platform has no real-money payment flow. Not eligible for realized-cash goal.
- Main Bounty lifecycle ledger and event recovery now added. Run 42900051461 succeeded with 37 unit tests; no API keys present, so authenticated Bounty reads, event recovery and model drafting were clean idle modes. A unit test prints mocked two-event page coverage; do not misreport this as actual live event retrieval.
- Next: validate live public BountyBoard API in Actions, review task detail/escrow state and AI permission, then rank only tasks with cash payout, funded escrow, explicit agent permission, no physical presence and acceptable unit economics.
