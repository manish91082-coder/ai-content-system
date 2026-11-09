# AgentGuard — Policy-Bound Agent Payments

**NEAR HACKATHON 2026 | Tracks: Agent Economy + AI Security & Defense**

AgentGuard is a safety gateway for autonomous agents that need to earn, spend, hire other agents and pay for APIs without receiving unrestricted control of a wallet.

## The problem
An autonomous agent may be manipulated by prompt injection, deceptive task instructions or a malicious counterparty into making an irreversible payment. A normal LLM instruction such as "do not pay this address" is not an enforceable financial control.

## What this prototype demonstrates
1. An agent proposes a payment.
2. A deterministic policy engine checks the recipient, method, contract, amount, rolling spend limit and risk signals.
3. The gateway returns **ALLOW**, **WARN** or **BLOCK** with machine-readable reasons.
4. The signing boundary is called only for ALLOW. WARN requires an explicit human approval token; BLOCK cannot be overridden by the agent.
5. Every decision is written to a tamper-evident SHA-256 hash-chained receipt log.
6. A prompt-injection attack demo tries to route a payment to a blocked recipient and is stopped before the signing boundary.

## Safety model
- This prototype never stores a seed phrase or private key.
- The demo signing adapter is intentionally a stub. It does not broadcast transactions or move funds.
- A production NEAR integration must use a scoped FunctionCall access key or a policy-bound Agent API wallet, never a FullAccess key for the autonomous worker.
- Contract allowlists, method allowlists, per-transaction caps, daily caps and human approval thresholds are enforced outside the LLM.
- A FunctionCall key is not a general-purpose transfer key. NEAR access-key limitations and gas allowance failure modes must be understood before deployment.

## Run
```bash
python -m pip install -e ".[dev]"
python demo/run_attack_demo.py
pytest -q
```

Expected demo: the benign payment is allowed in simulation; the prompt-injected payment to `bad.actor.near` is blocked; the signing adapter is not invoked for the blocked action.

## Architecture
```text
Task / Agent proposal
        |
        v
Policy Gateway -----> Counterparty signals / blocklist
        |                         |
        v                         v
ALLOW / WARN / BLOCK <--- Deterministic policy evaluation
        |
        +---- BLOCK: stop + receipt
        |
        +---- WARN: human approval token required
        |
        +---- ALLOW: scoped signer adapter (stub in this prototype)
                          |
                          v
                 Receipt + hash-chain audit
```

## Scope and limitations
The first milestone is an executable local policy and attack demonstration, not a claim of deployed NEAR mainnet functionality. NEAR testnet / Agent API integration is a subsequent adapter milestone after the exact API and key constraints are validated. No real funds are used.

## Fresh-work disclosure
The AgentGuard implementation in this directory is newly authored for the NEAR HACKATHON build window. The parent repository contains unrelated pre-existing work; this directory is the isolated hackathon project. No pre-existing product or customer traction is claimed.

## Track fit
- **AI Security & Defense:** policy engine, sandboxed spending controls, counterparty risk and prompt-injection defence.
- **Agent Economy:** safe agent-to-agent and agent-to-service payment authorisation.

## Security note
This is a prototype, not an audited wallet, custody service, smart contract or financial product. Do not connect a production wallet. Review all code and testnet integration before any real transaction.


## NEAR integration safety decision
The official NEAR Intents Agent API documentation describes the Agent API as an **experimental, mainnet-only beta** and warns that assets may be lost. Its quickstart uses real funds (approximately 10 USDC) and there is no testnet version. This prototype therefore does not connect to that beta or request real funds. A later integration must first be reviewed against the current API docs and require explicit owner approval; no partner API key or grant token may be placed in a browser or model prompt.

For the hackathon proof, prefer a NEAR testnet contract plus a narrowly scoped FunctionCall access key, subject to contract implementation and testnet validation. Such a key cannot make native transfers or replace account keys; the contract must itself enforce the spending policy and control any test funds. This is a design target, not yet implemented or deployed.
