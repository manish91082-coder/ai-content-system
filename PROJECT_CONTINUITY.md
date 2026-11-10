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
