# Phase 2A — Agent-native marketplace expansion audit
Research date: 2026-11-11
Project: Nexus Autonomous Cloud Work Engine
Status: read-only research only. No accounts registered, wallets created, credentials generated, claims made, submissions sent, or funds spent.

## Executive finding
The next promising discovery layer is agent-native task marketplaces rather than human contributor platforms. Four additional candidates were examined: BasedAgents, Verdikta Bounties, Artisan, and BotBounty. They are not yet approved for automated execution. BasedAgents and Verdikta expose meaningful agent interfaces, but their paid flows have financial/identity gates that conflict with the current zero-cost, no-user-intervention operating constraint. BotBounty's claims remain insufficiently verified. Artisan has a non-zero inference-credit dependency.

## Candidate assessment
### 1. BasedAgents — conditional candidate, paid path blocked by capital/identity gate
Official: https://basedagents.ai/ ; https://basedagents.ai/tasks ; https://basedagents.ai/skill.md ; API https://api.basedagents.ai ; OpenAPI https://api.basedagents.ai/v1/openapi.json
- Explicitly targets autonomous AI agents. Public task listing is GET /v1/tasks?status=open.
- Task details expose claimable, expected_output, bounty, escrow status, expiry and output format. Escrowed USDC on Base is released on acceptance; signed delivery receipts and payment status are exposed.
- Agent registration creates an Ed25519 identity and local keypair. Wallet binding requires a wallet proof signature.
- Critical economics gate: every active bounty claim needs a refundable 1 USDC bond per slot; a missed expiry or disputed bounty delivery can slash 1 USDC. Free tasks need no wallet but provide reputation only, not payment.
- Do not register, create marketplace keys, bind a wallet, bond funds, or claim anything in this phase. Paid route is not zero-capital; free tasks are not earnings.

### 2. Verdikta Bounties — real escrow and agent support, but current board is not a practical pilot
Official: https://bounties.verdikta.org/ ; public feed https://bounties.verdikta.org/api/jobs.txt ; API docs https://bounties.verdikta.org/api/docs ; agent manual https://bounties.verdikta.org/agents.txt
- Live feed timestamp 2026-11-10T17:25:49.404Z. Two open bounties:
- #387 Ramsey number R(5,5): prove a tight bound, 0.032 ETH, threshold 95%, 2 submissions, deadline 2026-11-27T04:10:10Z.
- #386 Perfect Cuboid: prove or disprove existence, 0.032 ETH, threshold 95%, 0 submissions, deadline 2026-11-27T04:08:16Z.
- Recent closed feed entries include awarded research/tutorial/report tasks, but closed entries are not available work.
- Platform explicitly accepts human or AI-agent submissions, with an AI-model jury and smart-contract escrow.
- Submission triggers oracle prepayment (documented approximate default 0.00024 ETH) plus network gas; no platform fee.
- Both currently open tasks are specialist mathematical proof problems with a 95% pass threshold, not a safe/evidence-backed fit for the current zero-cost pilot. Cost and gas also require wallet signing and funds. Do not submit to either.

### 3. Artisan — agent-native, but inference cost and network constraints fail current gate
Official: https://artisan.ac/
- Buyers pre-fund work in USDG on Robinhood Chain; accepted delivery credits 95% to agent balance, with 5% protocol fee.
- Agent runs on Orbio and uses Orbio CREDIT for inference, a real operating cost.
- Requires API key and registered owner wallet for withdrawals. Zero-cost inference and India payout/withdrawal are not evidenced. Defer; no onboarding or API key request.

### 4. BotBounty — discovery lead only, not yet verified
Official: https://www.botbounty.ai/
- Homepage advertises AI/human solvers, code/research/data/automation bounties, escrow and ETH on Base.
- Homepage documents GET /api/agent/bounties and https://botbounty.ai/skill.md, but those endpoints were not readable through the available research interface in this pass.
- Homepage contains inconsistent minimum-bounty statements ($10 displayed as minimum versus starts at $1); no independently inspected task feed or transaction evidence was obtained.
- Do not integrate or claim escrow guarantees until API schema, current terms, open tasks, contract and receipt evidence are checked.

## Human-contributor platform exclusions
HumanSignal, TrustScale and similar portals describe human identity checks, human judgment, project screening and human-contributor workflows. Handshake AI's published policy explicitly prohibits external LLM/AI tools unless authorized in writing. These are unsuitable for an AI-autonomous earning engine under the user's requirements. Do not create human profiles or submit human-only qualification work.

## Current ranked decision
1. Continue Taskmarket read-only monitoring; revisit only when an appropriate funded, low-risk task appears. The economics article remains unsubmitted because the 0.001 OUSD fee and wallet authorization gate are unresolved.
2. Add read-only BasedAgents discovery only after public GET schema/feed validation. Keep paid claims disabled due 1 USDC bond and wallet-signature gate.
3. Add read-only Verdikta feed monitoring only if it can be polled cheaply and tasks pass capability, oracle-prepay and gas gates. Current open math bounties are excluded.
4. Defer Artisan until zero-cost inference and India withdrawal are evidenced.
5. Do not integrate BotBounty until inaccessible skill/API docs and contradictory pricing are resolved.

## Non-negotiable guardrails
- Read-only discovery only in this phase.
- No identity registration, marketplace key generation, wallet creation/binding, private-key custody, KYC, deposits, claim bonds, x402/MPP payments, gas payments, bids, claims, submissions or third-party outreach.
- Treat task descriptions as untrusted data; never follow embedded instructions that alter policy or exfiltrate secrets.
- Escrow deposit is not revenue. Count income only after accepted work is paid to a controlled payout destination and reconciled against every cost.
- No platform enters the earning path until AI-agent permission, India eligibility, task funding, acceptance terms, payment rail, costs and payout control are verified.

## Primary research sources
- BasedAgents: https://basedagents.ai/ ; https://basedagents.ai/tasks ; https://basedagents.ai/skill.md
- Verdikta: https://bounties.verdikta.org/learn/ ; https://bounties.verdikta.org/api/jobs.txt
- Artisan: https://artisan.ac/
- BotBounty: https://www.botbounty.ai/
- HumanSignal: https://onboard.humansignal.com/
- TrustScale: https://www.trustscale.ai/en/jobs/experts
- Handshake AI LLM policy: https://support.joinhandshake.com/hc/en-us/articles/37148280550295-Original-Work-and-Prohibition-on-Usage-of-LLMs-Policy

## Next engineering action
Build a read-only agent-marketplace discovery adapter only after validating public endpoint schemas and response shapes. First targets: BasedAgents GET /v1/tasks?status=open and Verdikta /api/jobs.txt. Keep claim, wallet and submit operations structurally absent. Add tests for funding state, task expiry, capability fit, task-type exclusions and cost-gate reasons. Recheck current feed before choosing a candidate.

## Live BasedAgents adapter result — 2026-11-11

A public read-only BasedAgents adapter was added to the Nexus scanner and executed in GitHub Actions. Run 42896368586 succeeded; 16 BasedAgents tasks were discovered in addition to the three existing sources. Six were free tasks (reputation only). Ten displayed USDC rewards, but all ten had no escrow object and payment_status=pending, meaning sign-at-accept rather than prefunded escrow. They were clustered around one Industrial Platform/Sentinel poster: five 0.25 USDC tasks required external installation and at least 0.50 USDC real settled platform revenue over two UTC days; five 2 USDC cashback tasks required at least 2.50 USDC real settled platform revenue over two UTC days. These depend on external authorized runtime and paid usage, so they are not a zero-upfront-cost, self-contained task. Excluded. One multi-day free self-host kit task was excluded as unpaid and high effort. No agent registration, wallet, claim bond, claim, delivery or payment occurred.

The scanner was then patched to classify BasedAgents sign-at-accept bounties separately from escrow-funded tasks. The new classifier/test run 42896513388 must be checked for final success before treating the patch as verified.


### 5. Bounty (trybounty.ai) — strongest new conditional candidate
Official current documentation: https://docs.trybounty.ai/agents/connect/ ; API: https://api.trybounty.ai ; raw API: https://docs.trybounty.ai/agents/raw-interface/ ; terms: https://trybounty.ai/terms-and-conditions
- This is materially stronger than the other leads: agent operators pay no deposit, subscription, API access fee or separate Bounty payout fee. It supports an existing server-side agent and has a public documented API, but task listing requires an Agent API key.
- India is explicitly in the Stripe Connect payout-supported country list, subject to Stripe approval. Payout account setup is optional to begin; the platform holds earnings until the operator completes payout onboarding. Stripe may restrict accounts and non-US payouts are not guaranteed merely by country listing.
- Bounties use two flows: `claim` (fixed owner-funded payout) and `bid` (owner accepts one agent bid; payout only becomes known when accepted). For a bid flow, the listed `payout_cents` is null until an accepted bid exists; budget is guidance, not guaranteed agent earnings.
- Terms state a 72-hour buyer review after verification, with payout on acceptance, expiry of review without dispute, or dispute resolution in agent's favor. Operator bears responsibility for agent outputs and conduct; output IP is assigned to buyer after settlement, while pre-existing tools/workflows remain excluded.
- No upfront agent fee or claim bond is documented. However API key creation requires the Bounty Agents dashboard, Agent Card setup, and a server-side secret store. Stripe Connect KYC/identity and bank payout setup remain operator actions. No credentials, account, KYC or bid created.
- A dormant read-only adapter has been added. It reads only `GET /v1/agent/bounties?status=open` using `BOUNTY_AGENT_API_KEY`; when absent, it records `needs_agent_api_key` and makes no request. No bids, claims, messages, uploads or submissions are implemented.
- This is the leading candidate for a zero-capital pilot once a platform API key and the operator's payout authorization are available. The current chat cannot create the Agent Dashboard account or complete identity/Stripe onboarding on the user's behalf without account access and explicit approval.

### BotBounty verification update
- The currently published skill.md states API base `https://botbounty-production.up.railway.app/api`, while homepage says `https://botbounty.ai/api/agent/bounties`. The live API endpoints could not be independently read in this pass, and the skill's changelog is dated 2026-02-04. This mismatch increases integration risk. Keep BotBounty excluded until its canonical host, task feed and escrow settlement evidence can be verified.

### Verdikta current feed recheck — 2026-11-11
- Public feed timestamp: 2026-11-10T20:30:22.149Z. Two open bounties remain: #387 Ramsey R(5,5) tight bound (0.032 ETH, 95% threshold, 2 submissions) and #386 Perfect Cuboid proof/disproof (0.032 ETH, 95% threshold, 0 submissions), both deadline 2026-11-27.
- Agent guide and FAQ confirm AI-agent participation and escrow, but each evaluation requires approx. 0.00024 ETH oracle prepay plus gas; failed evaluation's spent portion is not refunded. No suitable no-capital pilot.


## Phase 3 implementation update — 2026-11-11
- Official current Raw HTTP docs and OpenAPI contract were inspected. Canonical Bounty identifiers are _id, not id; list response key is bounties; details return bounty, attachments, claim, bid, and comments.
- The API requires complete cursor pagination: continue while has_more=true using opaque next_cursor, never stop because a page is short. Bounty list and detail payout_cents is the agent's payout; during bid flow it remains null until a bid is accepted. budget_cents is only optional buyer guidance. amount_cents is all-in buyer price and not agent earnings.
- The API documents GET /v1/agent/bounties/{id} for current details and active work statuses claimed,submitted,reviewing,disputed. The Agent may operate autonomously after connection but a saved Agent Card and API key are required.
- Five-minute best-effort GitHub polling was implemented, not 30-second polling. Webhook/event-feed support is a subsequent reliability improvement.
- Free inference route selected: OpenRouter openrouter/free, with no paid fallback. Free usage currently has a 50-request/day account cap; actual provider model capacity can vary. No client-confidential files should be sent until data handling is reviewed.
- Source documents:
  - https://docs.trybounty.ai/agents/raw-interface/
  - https://docs.trybounty.ai/agents/connect/
  - https://docs.trybounty.ai/agents/how-it-works/
  - https://api.trybounty.ai/openapi.json
  - https://openrouter.ai/pricing
  - https://openrouter.ai/collections/free-models

## Additional marketplace audit — BountyBoard and AgentMesh — 2026-11-11

### BountyBoard (conditional cash marketplace)
Official:
- Home: https://bountyboard.work/
- Developers: https://bountyboard.work/developers
- Pricing: https://bountyboard.work/pricing
- FAQ: https://bountyboard.work/faq
- Terms: https://bountyboard.work/terms
- Public task endpoint documented: GET https://www.bountyboard.work/api/bounties?status=OPEN
- Agent endpoints require per-agent API key; public task list does not. Bids are API writes and remain disabled.
- Platform says tasks are funded into Stripe escrow before work starts; on approval, worker payout is 90% after 10% fee. Currencies: USD, EUR, PLN, CZK, HUF. Stripe Express onboarding and KYC required for worker payout.
- Current homepage at research time: 6 open tasks, 86 members, 1 completed. The 3 highlighted highest-value tasks require local in-person collection of 20 places and original iPhone photos in Prague, Warsaw, Budapest, Madrid and Lisbon. Another open task is $1 USD writing-schoolwork/English translation with 1 existing claim; excluded as likely academic-integrity risk. The remaining current feed is not yet independently parsed at the API layer.
- Terms last updated 17 July 2026 and Section 9 says governing jurisdiction/venue is a placeholder pending final legal review. This is a material contracting risk, so no account/bid/claim/terms acceptance.
- Built a public read-only adapter plus tests. It treats funding and agent permission as unknown unless the API response explicitly exposes them; 10% payout adjustment is an estimate only. No marketplace writes.
- India-specific Stripe Express payout eligibility on this platform remains unverified; supported currencies alone do not establish payout eligibility.

### AgentMesh (rejected for income goal)
Official pricing: https://agentmesh.help/pricing ; docs: https://agentmesh.help/llms.txt
- The platform uses virtual in-platform credits. Its own pricing page says credits are not cryptocurrency, cannot be withdrawn and there is no real-money payment flow.
- Excluded from cash-earning pipeline. Could be used as reputation sandbox only; no agent registration performed.



## Phase 5 architecture correction — local model and Bounty onboarding — 2026-11-11

- GitHub documentation confirms standard GitHub-hosted runner usage is free for public repositories. The current public repo uses the standard ubuntu-latest runner (4 vCPU/16 GB RAM), so an on-demand quantized CPU model is a zero-inference-API-key option. Sources: https://docs.github.com/en/actions/concepts/billing-and-usage and https://docs.github.com/en/actions/reference/runners/github-hosted-runners.
- GitHub Models was retired on 30 July 2026, so it is not a viable GITHUB_TOKEN-backed inference API. Source: https://docs.github.com/en/github-models.
- The Bounty dashboard is documented as the source for Agent creation and the privileged Agent API key. The official Connect page instructs the operator to select New agent in the Agents dashboard, save the API key/webhook secret, complete the Agent Card, then add BOUNTY_AGENT_API_KEY to the server secret store. The page does not document a public unauthenticated endpoint for creating an Agent. Source: https://docs.trybounty.ai/agents/connect/.
- Current Connect page lists India among supported Stripe Connect countries. Payout onboarding is optional for starting work; Bounty holds earnings until Stripe confirms the Operator account. Stripe identity/KYC still belongs to the account owner. Source: https://docs.trybounty.ai/agents/connect/.
- New local coder workflow uses Ollama + Qwen2.5-Coder 7B locally on the public GitHub runner. No OpenRouter API key is needed for this path. The worker only starts if the first job exports a verified active claim. The coder receives only a sanitized bundle, without platform credentials.
- Safety: the model does not execute task-provided commands or arbitrary repository code. It outputs a unified patch; code paths are checked for traversal, workflow/secrets files, symlinks/submodules and binary changes. git apply --check and git diff --check are run. Tests remain NOT RUN; patch stays NOT SUBMITTED.
