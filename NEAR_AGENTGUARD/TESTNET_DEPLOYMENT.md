# AgentGuard NEAR Testnet Deployment

This procedure uses testnet faucet tokens only. Never use a mainnet account, seed phrase in chat, or real funds.

## Account design

- OWNER_ACCOUNT: your own named NEAR testnet account. Its full-access key stays in your OS keychain and is used only for administration.
- CONTRACT_ACCOUNT: a child account created for AgentGuard. It holds only testnet treasury funds.
- WORKER_ACCOUNT: a separate child account registered as an agent. Its FullAccess key is removed after a scoped FunctionCall key is installed.
- RECIPIENT_ACCOUNT: a testnet account that is explicitly allowlisted.

The worker key is restricted to one receiver (CONTRACT_ACCOUNT) and one method (pay), with a small gas allowance. The FunctionCall key cannot transfer NEAR by itself. The contract treasury executes the native transfer after enforcing the on-chain policy.

## Prerequisites

Install Rust and near-cli-rs. Official CLI: https://near.cli.rs/
Import your testnet owner account into the OS keychain using the testnet wallet flow. Do not paste or send private keys to anyone.

Check:
~~~bash
near --version
cargo --version
~~~

The owner account should have at least 1.2 testnet NEAR to create and fund the contract and worker subaccounts, plus gas. Use faucet test tokens only.

## Recommended automated path

From WSL, run the deployment script:

~~~bash
cd NEAR_AGENTGUARD
chmod +x scripts/deploy_testnet.sh
OWNER_ACCOUNT=your-name.testnet RECIPIENT_ACCOUNT=recipient.testnet ./scripts/deploy_testnet.sh
~~~

The script creates:
- agentguard.your-name.testnet
- agentguard-worker.your-name.testnet

It deploys and initializes the contract, allowlists the recipient, registers the worker, creates a FunctionCall access key restricted to method pay, removes the worker's FullAccess key on-chain, and executes one 0.001 NEAR testnet payment.

The script uses your local NEAR CLI keychain. It does not read or transmit private keys.

## Automated least-privilege gate

Before it registers the worker or attempts the test payment, the script checks that the worker has exactly one on-chain access key, that its public key matches the newly-created FunctionCall key, that no FullAccess permission remains, and that the visible permission is restricted to the AgentGuard contract's `pay` method. If any check fails, the script stops before the 0.001 NEAR testnet transfer.

## Manual verification after the script

1. Inspect the contract account and transaction on https://explorer.testnet.near.org/
2. Run the CLI list-keys command for the worker account. It must show only a FunctionCall key with receiver_id equal to the contract account and method_names containing only pay.
3. View get_policy and confirm limits and freeze state.
4. Confirm the recipient balance increased by 0.001 NEAR.
5. Confirm the contract log contains AgentGuardPaymentAuthorized.

## Security boundaries

- This is a testnet-only prototype, not an audited wallet or custody product.
- The contract account remains the treasury and its FullAccess key must remain offline/owner-controlled.
- The worker must not retain a FullAccess key.
- Never deploy to mainnet for the hackathon demo.
- If any step fails, stop. Do not bypass the FunctionCall restriction or add a FullAccess key to the agent.
- The daily cap is conservative accounting. A failed native transfer can still consume the contract's spend counter; this is a known prototype limitation and must be disclosed.
