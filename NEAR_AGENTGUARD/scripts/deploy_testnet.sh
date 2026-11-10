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

echo "Capturing the worker's original FullAccess public key..."
mapfile -t ORIGINAL_KEYS < <(
  near account get-public-key from-keychain "$WORKER_ACCOUNT" network-config testnet \
    | grep -oE 'ed25519:[A-Za-z0-9]+' || true
)
if [[ "${#ORIGINAL_KEYS[@]}" -ne 1 ]]; then
  echo "Expected exactly one newly-created worker key; found ${#ORIGINAL_KEYS[@]}. Stop and inspect the local keychain." >&2
  exit 1
fi
WORKER_FULL_KEY="${ORIGINAL_KEYS[0]}"

echo "Adding worker FunctionCall key restricted to this contract/pay..."
ADD_KEY_OUTPUT="$(near account add-key "$WORKER_ACCOUNT" \
  grant-function-call-access \
  --allowance '0.05 NEAR' \
  --contract-account-id "$CONTRACT_ACCOUNT" \
  --function-names pay \
  autogenerate-new-keypair save-to-keychain \
  network-config testnet sign-with-keychain send)"
printf '%s\\n' "$ADD_KEY_OUTPUT"
mapfile -t FUNCTION_CALL_KEYS < <(
  grep -oE 'Added access key = ed25519:[A-Za-z0-9]+' <<< "$ADD_KEY_OUTPUT" \
    | grep -oE 'ed25519:[A-Za-z0-9]+' || true
)
if [[ "${#FUNCTION_CALL_KEYS[@]}" -ne 1 ]]; then
  echo "Could not identify exactly one newly-created FunctionCall key. Do not delete the existing FullAccess key." >&2
  exit 1
fi
WORKER_FUNCTION_KEY="${FUNCTION_CALL_KEYS[0]}"
if [[ "$WORKER_FUNCTION_KEY" == "$WORKER_FULL_KEY" ]]; then
  echo "New FunctionCall key unexpectedly matches the original key. Stop." >&2
  exit 1
fi

echo "Removing the original worker FullAccess key on-chain..."
near account delete-keys "$WORKER_ACCOUNT" public-keys "$WORKER_FULL_KEY" \
  network-config testnet sign-with-keychain send

echo "Verifying least-privilege access before any payment..."
ACCESS_KEYS_OUTPUT="$(near account list-keys "$WORKER_ACCOUNT" network-config testnet now)"
printf '%s\\n' "$ACCESS_KEYS_OUTPUT"
mapfile -t REMAINING_KEYS < <(
  grep -oE 'ed25519:[A-Za-z0-9]+' <<< "$ACCESS_KEYS_OUTPUT" || true
)
if [[ "${#REMAINING_KEYS[@]}" -ne 1 || "${REMAINING_KEYS[0]}" != "$WORKER_FUNCTION_KEY" ]]; then
  echo "Worker must have exactly the one newly-created FunctionCall key. No payment will be attempted." >&2
  exit 1
fi
if grep -Eiq 'full access' <<< "$ACCESS_KEYS_OUTPUT"; then
  echo "A FullAccess key remains on the worker. No payment will be attempted." >&2
  exit 1
fi
if ! grep -Fq "only do [\\"pay\\"] function calls on $CONTRACT_ACCOUNT" <<< "$ACCESS_KEYS_OUTPUT"; then
  echo "Worker key is not visibly scoped to this contract and pay method. No payment will be attempted." >&2
  exit 1
fi

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
