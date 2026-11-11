# AgentGuard NEAR testnet contract

This contract is the on-chain enforcement layer. Only owner-registered agent accounts can invoke `pay`; the contract enforces an allowlisted recipient, explicit blocklist, per-payment ceiling, rolling UTC-day spend cap and emergency freeze before creating a native NEAR transfer promise.

## Security properties
- Owner-only policy administration.
- No arbitrary recipient payments.
- Unknown recipients fail closed.
- Agent revocation and emergency freeze.
- Checked arithmetic for spend accounting.
- No attached deposits accepted by `pay`.
- No private key, seed phrase, signer or external API credential stored in contract state.

## Important limitation
This is a hackathon prototype contract, not an audited custody product. The contract account is the treasury: only fund it with valueless testnet NEAR. The owner must keep the contract account's full-access credentials offline. An agent should call only the deployed contract's `pay` method through a FunctionCall access key scoped to this contract and method, with a small gas allowance. The contract still checks the caller and all policy rules; the access key is not itself the policy.

## Build and test
Install Rust and the NEAR target, then run:
```bash
cargo test
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

Do not deploy until tests pass. Deploy only to NEAR testnet, fund only with faucet test tokens, and verify the contract account, code hash, access-key scope and transaction receipts.

## License

This contract is part of the `NEAR_AGENTGUARD/` project and is covered by [the project MIT License](../LICENSE).
