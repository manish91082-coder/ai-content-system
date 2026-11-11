# AgentGuard — 2:50 Demo Recording Plan

The final video must show the real executable prototype. Do not claim a production wallet, mainnet deployment or audited security product.

## 0:00–0:20 — Threat
Show the title and architecture.
Narration: "Autonomous agents can be manipulated into unsafe payments. AgentGuard places deterministic policy between an agent and its payment signer."

## 0:20–0:55 — Python policy gateway
Run:
~~~bash
cd NEAR_AGENTGUARD
python -m pip install -e ".[dev]"
python demo/run_attack_demo.py
~~~
Show the benign ALLOW and malicious BLOCK. Highlight that the simulated signer is never called for BLOCK.

## 0:55–1:30 — Human approval and receipt security
Show tests for exact-intent approval, expiry, replay refusal, BLOCK non-overridable behavior, and tamper-evident receipt chain.

## 1:30–2:05 — NEAR contract validation
Show GitHub Actions: Rust unit tests and WASM release build passing. Open the contract methods for register_agent, allow_recipient, set_frozen and pay.

## 2:05–2:35 — Testnet least-privilege proof (only after testnet deployment)
Show the deployed contract, get_policy view, worker access-key list showing only a FunctionCall key scoped to the contract and pay method, and the 0.001 NEAR testnet payment receipt. Do not show private keys.

## 2:35–2:50 — Limitations
Narration: "This is a testnet-only prototype. The signer demo does not move funds. No mainnet funds are used. The project targets AI Security and Defense."

## Final checks
- Video under 3 minutes.
- Public YouTube link.
- Public repository link.
- Public X post with @NEARProtocol and #NEARHackathon.
- Submission form includes the actual NEAR wallet address.
- Never show private keys, seed phrases or real credentials.
