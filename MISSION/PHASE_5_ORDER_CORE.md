# Phase 5 — Executable Order Core

## Delivered in this phase

- Local SQLite order ledger with immutable product-version and integer minor-unit price snapshots.
- Normalized payment-event inbox with provider + environment + event ID deduplication.
- Amount/currency/order validation before changing entitlement.
- Forward-only payment state handling: late failure cannot undo a capture; late capture cannot restore a refunded/disputed order.
- One fulfilment job per order + operation; completion is idempotent.
- HMAC-SHA256 raw-body signature verification helper.
- Automated regression tests for duplicates, mismatches, pending payments, late/out-of-order events, refunds, disputes and fulfilment retries.

## Safety boundary

This is a local execution core, not a payment gateway integration. It does not create checkout links, receive HTTP requests, verify a provider-specific webhook header format, deliver files, send customer messages, issue refunds or reconcile bank settlements. The caller must verify the provider signature over the exact raw request bytes before parsing and passing a normalized event to `process_payment_event`.

Do not expose SQLite or this module as a public payment endpoint. Do not mark a payment event trusted merely because its JSON says `captured`. Provider-specific adapters, server-side payment-status verification, private storage, authenticated delivery, refund/dispute workflows and bank reconciliation remain separate implementation tasks.

## Run locally

```bash
python -m unittest tests.test_order_core -v
```

The test suite uses temporary local databases and fake provider events. It sends no network requests and does not move money.

## Next phase

Add a provider-specific sandbox adapter only after the merchant account, exact webhook signing contract and sandbox credentials are available. Then add private asset delivery and settlement reconciliation. Live checkout remains disabled until explicit owner authorization.
