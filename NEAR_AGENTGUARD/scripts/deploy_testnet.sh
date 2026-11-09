#!/usr/bin/env bash
set -euo pipefail

: "${OWNER_ACCOUNT:?Set OWNER_ACCOUNT to your own NEAR testnet account}"
: "${RECIPIENT_ACCOUNT:?Set RECIPIENT_ACCOUNT to an existing NEAR testnet account}"

CONTRACT_ACCOUNT="${CONTRACT_ACCOUNT:-agentguard.${OWNER_ACCOUNT}}"
WORKER_ACCOUNT="${WORKER_ACCOUNT:-agentguard-worker.${OWNER_ACCOUNT}}"
WASM="contract/target/wasm32-unknown-unknown/release/agentguard_contract.wasm"

if ! command -v near >/dev/null 2>&1; then
  echo "near-cli-rs is required. Install it from https://near.cli.rs/" >&2
  exit 1
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "Rust/Cargo is required." >&2
  exit 1
fi

echo "Building AgentGuard WASM..."
(
  cd contract
  cargo build --target wasm32-unknown-unknown --release
)

echo "Creating contract treasury account: $CONTRACT_ACCOUNT"
near account create-account fund-myself "$CONTRACT_ACCOUNT" '1 NEAR' \
  autogenerate-new-keypair save-to-keychain sign-as "$OWNER_ACCOUNT" \
  network-config testnet sign-with-keychain send

echo "Deploying and initializing contract..."
near contract deploy "$CONTRACT_ACCOUNT" use-file "$WASM" \
  with-init-call new \
  json-args "{\"owner\":\"$OWNER_ACCOUNT\",\"max_single\":\"10000000000000000000000\",\"daily_limit\":\"50000000000000000000000\"}" \
  prepaid-gas '100 TGas' attached-deposit '0 NEAR' \
  network-config testnet sign-with-keychain send

echo "Creating worker account..."
near account create-account fund-myself "$WORKER_ACCOUNT" '0.1 NEAR' \
  autogenerate-new-keypair save-to-keychain sign-as "$OWNER_ACCOUNT" \
  network-config testnet sign-with-keychain send

echo "Capturing worker FullAccess public key before replacing it..."
WORKER_FULL_KEY="$(near account get-public-key from-keychain "$WORKER_ACCOUNT" network-config testnet | grep -oE 'ed25519:[A-Za-z0-9]+' | tail -n 1)"
if [[ -z "$WORKER_FULL_KEY" ]]; then
  echo "Could not identify worker FullAccess public key. Stop and inspect keychain." >&2
  exit 1
fi

echo "Adding worker FunctionCall key restricted to contract/pay..."
near account add-key "$WORKER_ACCOUNT" \
  grant-function-call-access \
  --allowance '0.05 NEAR' \
  --contract-account-id "$CONTRACT_ACCOUNT" \
  --function-names pay \
  autogenerate-new-keypair save-to-keychain \
  network-config testnet sign-with-keychain send

echo "Removing worker FullAccess key on-chain..."
near account delete-keys "$WORKER_ACCOUNT" public-keys "$WORKER_FULL_KEY" \
  network-config testnet sign-with-keychain send

echo "Registering worker and allowlisting recipient..."
near contract call-function as-transaction "$CONTRACT_ACCOUNT" register_agent \
  json-args "{\"agent\":\"$WORKER_ACCOUNT\"}" \
  prepaid-gas '30 TGas' attached-deposit '0 NEAR' \
  sign-as "$OWNER_ACCOUNT" network-config testnet sign-with-keychain send

near contract call-function as-transaction "$CONTRACT_ACCOUNT" allow_recipient \
  json-args "{\"recipient\":\"$RECIPIENT_ACCOUNT\"}" \
  prepaid-gas '30 TGas' attached-deposit '0 NEAR' \
  sign-as "$OWNER_ACCOUNT" network-config testnet sign-with-keychain send

echo "Checking worker access keys. Verify only the scoped FunctionCall key remains:"
near account list-keys "$WORKER_ACCOUNT" network-config testnet now

echo "Executing 0.001 NEAR testnet payment using the worker account..."
near contract call-function as-transaction "$CONTRACT_ACCOUNT" pay \
  json-args "{\"recipient\":\"$RECIPIENT_ACCOUNT\",\"amount\":\"1000000000000000000000\",\"memo\":\"AgentGuard testnet demo\"}" \
  prepaid-gas '50 TGas' attached-deposit '0 NEAR' \
  sign-as "$WORKER_ACCOUNT" network-config testnet sign-with-keychain send

echo "Reading contract policy..."
near contract call-function as-read-only "$CONTRACT_ACCOUNT" get_policy \
  json-args '{}' network-config testnet now

echo "DONE. Verify transaction receipts and balances on NEAR testnet explorer."
