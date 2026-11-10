# AgentGuard — Policy-Bound Agent Payments

**NEAR HACKATHON 2026 · AI Security & Defense**

AgentGuard places deterministic policy between an autonomous agent's payment intent and the payment-signing boundary. It is designed to stop prompt-injection attempts, untrusted recipients and spending-limit violations before an agent can authorize a transfer.

## Start here

The project is isolated in [`NEAR_AGENTGUARD/`](NEAR_AGENTGUARD/README.md). Follow that directory's README for the full architecture, threat model, limitations and reproducible commands.

Run the local demonstration:

```bash
cd NEAR_AGENTGUARD
python -m pip install -e ".[dev]"
python demo/run_attack_demo.py
pytest -q
```

Build and test the NEAR contract separately:

```bash
cd contract
cargo test
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

The local demo should show a benign scoped payment as ALLOW and a prompt-injection attempt to a blocked recipient as BLOCK, without calling the signer for the blocked action. The Rust contract independently enforces owner-registered agents, recipient allow/block lists, single-payment and UTC-day spend limits, and an emergency freeze.

## What is implemented

- Deterministic ALLOW / WARN / BLOCK policy; an AI model cannot override the policy result.
- Exact-intent, expiring, single-use HMAC approval for WARN decisions.
- Fail-closed recipient, contract and method controls.
- SHA-256 hash-chained local decision receipts with integrity verification.
- A Rust NEAR contract with owner-only administration and on-chain payment constraints.
- A testnet deployment helper that uses testnet accounts and faucet funds only; it is not part of the local demo.

## Evidence boundary

**The Python demo uses a non-broadcasting simulated signer. The Rust contract has not been deployed to NEAR testnet. No wallet has been connected, no real funds have moved, and no production custody or security audit is claimed.** Treat this as a hackathon prototype, not a production wallet or financial product.

## Hackathon provenance

This project is located in the dedicated branch `near-hackathon/agentguard-v0` and the `NEAR_AGENTGUARD/` directory. The parent repository contains unrelated pre-existing work. The branch comparison against `master` shows the isolated project changes:

[View the branch diff](https://github.com/manish91082-coder/ai-content-system/compare/master...near-hackathon/agentguard-v0)

The project targets **AI Security & Defense** only. It does not claim a complete Agent Economy workflow.

For the detailed project README, test commands, security limitations and fresh-work disclosure, see [NEAR_AGENTGUARD/README.md](NEAR_AGENTGUARD/README.md).
