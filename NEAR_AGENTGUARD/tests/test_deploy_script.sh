#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_SCRIPT="$ROOT/scripts/deploy_testnet.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/bin"
export PATH="$TMP/bin:$PATH"
export MOCK_NEAR_CALL_LOG="$TMP/near.log"
export MOCK_FULL_KEY="ed25519:FullMockKey0123456789"
export MOCK_FUNCTION_KEY="ed25519:FunctionMockKey0123456789"
export MOCK_CONTRACT_ACCOUNT="agentguard.owner.testnet"

cat > "$TMP/bin/cargo" <<'MOCK_CARGO'
#!/usr/bin/env bash
set -euo pipefail
exit 0
MOCK_CARGO

cat > "$TMP/bin/near" <<'MOCK_NEAR'
#!/usr/bin/env bash
set -euo pipefail
printf '%s ' "$@" >> "$MOCK_NEAR_CALL_LOG"
printf '\n' >> "$MOCK_NEAR_CALL_LOG"

if [[ "${1:-}" == "account" && "${2:-}" == "get-public-key" ]]; then
  printf 'Public key (printed to stdout):\n%s\n' "$MOCK_FULL_KEY"
  exit 0
fi

if [[ "${1:-}" == "account" && "${2:-}" == "add-key" ]]; then
  printf 'Added access key = %s\n' "$MOCK_FUNCTION_KEY"
  exit 0
fi

if [[ "${1:-}" == "account" && "${2:-}" == "list-keys" ]]; then
  case "${MOCK_NEAR_MODE:-safe}" in
    safe)
      printf '1 | %s | only do ["pay"] function calls on %s with an allowance of 0.05 NEAR\n' \
        "$MOCK_FUNCTION_KEY" "$MOCK_CONTRACT_ACCOUNT"
      ;;
    full-access-remains)
      printf '1 | %s | full access\n' "$MOCK_FULL_KEY"
      printf '2 | %s | only do ["pay"] function calls on %s with an allowance of 0.05 NEAR\n' \
        "$MOCK_FUNCTION_KEY" "$MOCK_CONTRACT_ACCOUNT"
      ;;
    wrong-scope)
      printf '1 | %s | only do ["pay"] function calls on attacker.testnet with an allowance of 0.05 NEAR\n' \
        "$MOCK_FUNCTION_KEY"
      ;;
    *)
      echo "Unknown MOCK_NEAR_MODE" >&2
      exit 2
      ;;
  esac
fi

exit 0
MOCK_NEAR

chmod +x "$TMP/bin/cargo" "$TMP/bin/near"

run_deploy() {
  OWNER_ACCOUNT="owner.testnet" \
  RECIPIENT_ACCOUNT="recipient.testnet" \
  bash "$DEPLOY_SCRIPT"
}

# Case 1: valid single FunctionCall key scoped to AgentGuard/pay.
: > "$MOCK_NEAR_CALL_LOG"
export MOCK_NEAR_MODE="safe"
run_deploy > "$TMP/safe.out"
if ! grep -Fq "contract call-function as-transaction $MOCK_CONTRACT_ACCOUNT pay" "$MOCK_NEAR_CALL_LOG"; then
  echo "FAIL: safe test did not reach the testnet pay command" >&2
  exit 1
fi

# Case 2: if FullAccess remains, deployment must stop before registration/payment.
: > "$MOCK_NEAR_CALL_LOG"
export MOCK_NEAR_MODE="full-access-remains"
if run_deploy > "$TMP/full-access.out" 2>&1; then
  echo "FAIL: deployment continued despite a remaining FullAccess key" >&2
  exit 1
fi
if grep -Fq "contract call-function as-transaction $MOCK_CONTRACT_ACCOUNT pay" "$MOCK_NEAR_CALL_LOG" || grep -Fq "register_agent" "$MOCK_NEAR_CALL_LOG"; then
  echo "FAIL: unsafe key state reached a contract call" >&2
  exit 1
fi

# Case 3: if the FunctionCall key targets a different contract, stop before payment.
: > "$MOCK_NEAR_CALL_LOG"
export MOCK_NEAR_MODE="wrong-scope"
if run_deploy > "$TMP/wrong-scope.out" 2>&1; then
  echo "FAIL: deployment continued with the wrong FunctionCall receiver" >&2
  exit 1
fi
if grep -Fq "contract call-function as-transaction $MOCK_CONTRACT_ACCOUNT pay" "$MOCK_NEAR_CALL_LOG" || grep -Fq "register_agent" "$MOCK_NEAR_CALL_LOG"; then
  echo "FAIL: wrong receiver scope reached a contract call" >&2
  exit 1
fi

echo "PASS: valid scoped key proceeds; FullAccess and wrong-scope keys stop before contract calls."
