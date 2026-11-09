# Phase 4 — Customer Order, Delivery and Settlement Architecture

## Decision status
**Architecture approved for engineering design; no payment provider or product is approved for live launch yet.** The current candidate product hypothesis remains unvalidated. This document defines the provider-neutral control plane so a real paid pilot can be added without confusing payment intent, captured payment, fulfilment, payout or settled revenue.

The mission's ₹10 crore / 10–30 day objective remains a stretch target, not a forecast or guarantee. No orders, customers, payout account, payment gateway activation or settled revenue have been verified.

## 1. Payment-provider decision

### India-first candidate order
1. **Razorpay** — first integration candidate for direct India checkout after account approval. Its public pricing currently states zero setup fee and zero AMC, with a standard 2% transaction fee on successful payments plus applicable GST on the fee. Actual merchant offer, category eligibility, payment-method fees and settlement terms must be confirmed inside the approved merchant account.
2. **Cashfree** — alternate India gateway. Its published settlement guide describes standard T+2 settlements, subject to bank approval, transaction type, business category and risk parameters. Pricing and eligibility must be confirmed for the actual merchant account.
3. **Gumroad** — optional digital-product marketplace fallback, not the primary India checkout. Its official payout help page lists India bank payouts in INR, a $100 standard minimum balance, at least a 7-day holding period for weekly/monthly/quarterly payouts, and country-specific payout schedules. Bank payouts may take another 2–7 business days. This is materially different from direct domestic gateway settlement.

No provider is activated or selected conclusively until the account owner completes KYC, verifies the exact business category/product eligibility, sees the actual fee schedule and confirms the payout bank account. No integration will assume promotional pricing or instant settlement.

## 2. Canonical system boundaries

- **Catalogue:** immutable product version, description, price, currency, delivery type, refund terms and eligibility.
- **Checkout adapter:** creates the provider-side payment order/session using only server-calculated amount and currency.
- **Payment event inbox:** accepts signed server-to-server events, preserves event identity and verifies provider signature over the exact raw request body.
- **Order state machine:** one authoritative state per order; browser redirects never mark an order paid.
- **Fulfilment worker:** executes one idempotent delivery action after a captured/verified payment.
- **Private asset vault:** stores deliverables privately; short-lived signed URLs or authenticated delivery, never public Drive links by default.
- **Customer notification:** sends order confirmation and delivery status only after the corresponding database transaction commits.
- **Refund/dispute handling:** creates explicit refund and dispute records; never silently edits a completed payment.
- **Settlement ledger:** reconciles provider gross amount, fee, tax on fee, refunds, adjustments and bank credit.
- **Revenue evidence:** only net funds actually credited to the nominated bank account and reconciled against provider payout evidence count as settled cash revenue.

## 3. Order and payment state machines

### Order lifecycle
`draft → awaiting_payment → paid → fulfillment_pending → fulfilled`

Terminal or exception states:
- `payment_failed`
- `expired`
- `cancelled`
- `refund_pending`
- `partially_refunded`
- `refunded`
- `disputed`
- `chargeback`
- `fulfillment_failed` (recoverable, not a payment reversal)

### Payment lifecycle
`created → authorized → captured`

Other provider outcomes:
- `failed`
- `pending`
- `refunded`
- `partially_refunded`
- `disputed`
- `reversed`

Rules:
- An `authorized` payment is not treated as captured unless the selected provider's exact product and merchant configuration explicitly define the required confirmation.
- `pending` is non-terminal. Do not prompt a second payment or mark an order failed merely because the browser timed out.
- A browser success page is display-only. The backend verifies the payment through a signed webhook and/or provider server-side status API.
- Amount, currency, merchant account, provider order ID and internal order ID must match the server-created order.
- Out-of-order events must never regress `captured` to `authorized` or trigger duplicate delivery.

## 4. Database model (provider-neutral)

Proposed tables, subject to a reviewed migration and RLS design:
- `products`: stable product identity, active/inactive state.
- `product_versions`: immutable version, price, currency, delivery specification and refund terms.
- `orders`: internal order ID, customer reference, product version, amount, currency, status, timestamps.
- `payment_attempts`: provider, environment, provider order/payment IDs, amount, currency, status and idempotency key.
- `payment_webhook_inbox`: provider event ID, event type, signature result, raw-body digest, received time, processing status; unique provider/environment/event ID.
- `fulfillment_jobs`: order ID, operation type, idempotency key, attempts, lease/status, result reference.
- `deliveries`: order, asset reference, delivery channel, sent time, expiry and customer acknowledgement where available.
- `refunds`: provider refund ID, amount, reason, status and linked payment attempt.
- `settlements`: provider payout ID, gross amount, fees, tax on fees, adjustments, net amount, expected date and actual bank-credit date.
- `bank_statement_matches`: bank reference, credit date, amount, matched settlement and reconciliation status.
- `affiliate_attributions` and `commission_ledger`: optional, only after the first paid pilot and refund/chargeback rules are established.
- `audit_events`: append-only record of privileged changes and reconciliation decisions.

Money columns use integer minor units (paise for INR), not floating point. Product version and price are snapshotted into the order so later catalogue edits cannot change historical invoices. Provider IDs and event IDs are unique within provider + environment scope.

## 5. Webhook and idempotency protocol

1. Receive exact raw request bytes and provider signature headers.
2. Verify signature with the correct environment-specific webhook secret before parsing or taking action.
3. Persist the verified event to the inbox with a unique event key in a transaction.
4. Return a success acknowledgement only after durable receipt; if persistence fails, return a retryable failure.
5. Process the event asynchronously with a worker and a database lease/lock.
6. Fetch/verify payment status server-side where required; compare amount, currency and order linkage.
7. Apply only permitted forward state transitions.
8. Create at most one fulfilment job per order + fulfilment operation.
9. Record processing result and correlation IDs; retries must reuse the same idempotency identity.
10. Reconcile unresolved payments and payouts against provider APIs/reports and bank evidence.

Gateway delivery retries, worker retries, outbound API idempotency and customer payment attempts are separate mechanisms. A duplicate webhook must not create a second order, charge or delivery.

## 6. Digital delivery and privacy

- Store customer deliverables in a private storage bucket, not a public bucket or public Drive URL.
- Generate a short-lived signed URL only after an authenticated order entitlement check.
- Bind delivery to the immutable order and product version.
- Use one delivery job key per order; retry notification without regenerating or double-issuing the product.
- Minimise personal data. Store only fields required for checkout, invoice, delivery and support.
- Never place payment credentials, card data, UPI PINs, OTPs or service-role secrets in the application database.
- Email/WhatsApp delivery must use a provider and lawful consent; do not use unsolicited bulk messages.
- Customer data and downloadable files must not be sent to free AI inference providers unless the data is non-sensitive and the applicable provider terms are accepted.

## 7. Settlement and revenue accounting

Maintain distinct amounts:
- `gross_collected`: captured customer payments.
- `gateway_fees`: provider charges.
- `tax_on_gateway_fees`: provider tax charged on its fee.
- `refunds_and_chargebacks`: reversals and disputed amounts.
- `net_settlement_expected`: provider's expected bank payout.
- `bank_credit_confirmed`: actual bank-statement credit.
- `net_settled_revenue`: reconciled bank credit attributable to completed sales, net of applicable refunds/adjustments.

A successful checkout, captured payment, provider balance, pending payout or settlement report alone is not proof of actual bank credit. The dashboard must show separate counters and never sum them into a single "revenue" number.

## 8. Security and operational controls

- Keep provider API keys and webhook secrets in GitHub Actions secrets or a server-side secret manager; never in browser code, HTML, Git or logs.
- Separate sandbox and live credentials, webhook endpoints, database rows and idempotency namespaces.
- Use HMAC verification against raw request bytes and constant-time comparison where applicable.
- Restrict all exposed tables with RLS and minimum grants. Do not reuse the legacy `FOR ALL USING (true)` policies.
- No service-role key in a browser or client app.
- Privileged actions require authenticated actor identity and an append-only audit trail.
- Enforce price/amount server-side; ignore client-supplied amounts and order statuses.
- Add reconciliation alarms for paid-but-undelivered orders, delivered-but-unpaid orders, duplicate events, payout mismatches and refund ageing.
- Keep refunds and disputes available as explicit operational workflows before launch.

## 9. Zero-capital implementation sequence

1. Complete product/offer validation and choose the delivery type. Do not build a broad storefront before one offer has real buyer evidence.
2. Owner completes provider KYC and confirms eligibility, exact fees, settlement terms and bank payout route.
3. Implement provider sandbox adapter and webhook verification.
4. Implement order/payment tables, RLS, inbox deduplication and idempotent fulfilment.
5. Use a non-sensitive test product in sandbox and test duplicate, delayed, invalid-signature and out-of-order events.
6. Implement private file delivery, customer notifications and refund handling.
7. Reconcile sandbox reports and verify all state transitions.
8. Complete legal, tax, privacy, refund and platform policy review for the actual product and merchant entity.
9. Obtain explicit owner authorization before live checkout; start with a small controlled paid pilot.
10. Reconcile first real bank settlement manually against provider evidence before claiming revenue or automating broader scale.

No paid hosting, ads, paid APIs or upfront SaaS subscription is assumed. A payment gateway may deduct per-transaction fees, and KYC/account approval cannot be automated or bypassed. "Zero capital" therefore means no assumed prepayment budget, not zero operating cost or guaranteed provider approval.

## 10. Verified external references (checked 9 Nov 2026)

- Razorpay official pricing: https://razorpay.com/pricing/ — public standard pricing states 2% on successful payments, zero setup and zero AMC; confirm actual merchant offer and payment method.
- Razorpay webhook best-practices / verification: https://razorpay.com/docs/webhooks/best-practices/ — signature verification, raw body, retries, event IDs and replay handling.
- Razorpay Trust Portal checklist: https://security.razorpay.com/security/checklist/ — HMAC webhook validation and backend payment-status checks.
- Cashfree settlement and reconciliation: https://www.cashfree.com/settlement-and-reconciliation-guide/ — standard T+2 is subject to bank and risk conditions.
- Cashfree webhook verification: https://www.cashfree.com/devstudio/preview/pg/tools/webhookVerification — signature verification and idempotency.
- Gumroad payout guide: https://gumroad.com/help/article/13-getting-paid — India INR bank payout support, payout minimum, hold and timing.

Provider marketing pages are not a substitute for the merchant dashboard agreement, account-specific pricing or legal advice.
