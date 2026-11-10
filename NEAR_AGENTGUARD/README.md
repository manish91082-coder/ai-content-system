# AgentGuard — Policy-Bound Agent Payments

**NEAR HACKATHON 2026 | Primary track: AI Security & Defense**

AgentGuard is a deterministic security gateway for autonomous agents that request payments. It places enforceable policy between an agent's proposal and a signer, reducing the risk of prompt injection, malicious counterparties and uncontrolled spending.

## Threat model
An agent may receive adversarial task content that attempts to redirect funds, change a recipient, bypass limits or persuade the agent to ignore its instructions. LLM instructions alone are not a security boundary. AgentGuard applies deterministic checks outside the model.

## Prototype behavior
1. The agent proposes a payment intent.
2. A deterministic policy engine checks agent identity, recipient, contract, method, amount, daily spend and risk signals.
3. The gateway returns **ALLOW**, **WARN** or **BLOCK** with machine-readable reasons.
4. ALLOW reaches the demo signer. WARN requires a cryptographically authenticated approval token bound to the exact intent, expiring within a short window and usable once. BLOCK cannot be overridden.
5. Every decision is recorded in a SHA-256 hash-chained JSONL receipt log. The gateway refuses startup or append if the log is corrupt.
6. A prompt-injection demonstration attempts to pay a blocked recipient and is stopped before the signer boundary.

## Security controls in this prototype

- An empty recipient, contract or method allowlist fails closed; omission never means unrestricted access.
- No seed phrase or private key is stored.
- The demo signer returns SIMULATED_ONLY; it never broadcasts or transfers funds.
- Empty recipient allowlists fail closed.
- Configured contract and method allowlists are mandatory for each payment intent.
- Invalid/non-finite amounts, invalid spend counters and blocked recipients are rejected.
- Human approval is HMAC-authenticated, intent-bound, expiring and single-use in the in-process demonstration.
- Receipt integrity is checked before gateway startup and every append.

## Run locally
~~~bash
python -m pip install -e ".[dev]"
python demo/run_attack_demo.py
pytest -q
~~~

Expected behavior: the benign scoped payment is allowed in simulation; the prompt-injection attempt to bad.actor.near is blocked; the signer is not called for the blocked action.

## Architecture
~~~text
Agent proposal
     |
     v
Deterministic policy engine <--- Counterparty evidence
     |
     +---- BLOCK ---> receipt; signer never called
     |
     +---- WARN ----> exact-intent human approval required
     |                    |
     |                    +--> no/invalid/replayed/expired token: stop
     |                    +--> valid one-time token: demo signer
     |
     +---- ALLOW ---> demo signer
                          |
                          v
                   hash-chained receipt
~~~

## NEAR integration status
The Python signer is deliberately a stub. The Rust contract source is a separate testnet-oriented enforcement prototype. No NEAR deployment, wallet connection, real transaction or mainnet integration is claimed. A future testnet demonstration must use faucet funds only, a scoped FunctionCall access key, a verified contract build and reviewed deployment steps.

The NEAR Intents Agent API is experimental and mainnet-only in the reviewed documentation. This project does not use that beta or request real funds.

## Track fit
This implementation targets **AI Security & Defense**: deterministic spending controls, allowlisted recipients and methods, counterparty risk signals, ALLOW/WARN/BLOCK decisions, a signer boundary that refuses BLOCK, explicit human approval for WARN, and prompt-injection attack evidence.

It does not currently claim a complete Agent Economy workflow. Agent-to-agent hiring, paid service discovery and settlement would require a separate working feature set.

## Hackathon branch and baseline

This project is isolated in the `NEAR_AGENTGUARD/` directory on branch `near-hackathon/agentguard-v0`. The parent repository contains unrelated pre-existing work. Review the [branch diff against master](https://github.com/manish91082-coder/ai-content-system/compare/master...near-hackathon/agentguard-v0) to identify the hackathon project changes. This submission targets AI Security & Defense only; it does not claim a complete Agent Economy workflow.

## Fresh-work disclosure
The AgentGuard implementation in this directory is newly authored for the NEAR HACKATHON build window. The parent repository contains unrelated pre-existing work. No pre-existing product, users, customers or revenue are claimed.

## Limitations
This is a prototype, not an audited wallet, custody service, production signing system or financial product. The in-memory approval nonce store and process-local locks are suitable only for the local demonstration; production requires authenticated approval identity, durable atomic nonce storage, concurrency-safe spend accounting, external evidence provenance and independent security review. Do not connect a production wallet.

## License

This project directory is licensed under the MIT License. See [LICENSE](LICENSE). The license does not extend to unrelated content elsewhere in the parent repository.
