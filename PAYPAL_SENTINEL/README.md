# PayPal Sentinel — AI Checkout Firewall

**PayPal AI Hackathon 2026 | PayPal + AI | Agentic Commerce**

PayPal Sentinel is an AI-assisted checkout safety layer for agentic commerce. A buyer describes a purchase in natural language. Gemini extracts a proposed cart from a fixed catalog. A deterministic policy engine independently validates product, quantity, price, risk flags and spend limits. PayPal sandbox creates the order only after policy approval, and capture occurs only after the buyer approves in PayPal.

## Safety invariant

The AI model may propose a cart but never sets the payable amount, changes the catalog price, selects a different merchant, authorizes a payment, or captures funds. The server derives all prices from a fixed catalog. BLOCK never creates an order. WARN requires a short-lived, single-use approval bound to the exact plan. Even after policy approval, the buyer must separately approve in PayPal.

## Architecture

1. Natural-language request enters Gemini 3.8 Flash.
2. Gemini returns only a proposed SKU, quantity, risk flags and rationale.
3. Deterministic policy checks the SKU against the catalog and calculates the price using server-side Decimal values.
4. The policy returns ALLOW, WARN or BLOCK.
5. WARN requires a one-time approval token stored by hash in SQLite.
6. The backend reserves daily spend and creates a PayPal Orders v2 sandbox order using an idempotency key.
7. The buyer approves the payment in PayPal Checkout.
8. The backend atomically moves the order into a capture-in-progress state, captures it, and verifies COMPLETED status, currency and exact amount. An uncertain capture is frozen for reconciliation rather than retried blindly.

## Run locally

~~~bash
cd PAYPAL_SENTINEL
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / WSL:
# source .venv/bin/activate
python -m pip install -e ".[dev]"
copy .env.example .env
~~~

Fill these variables in the local .env file:
- PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET from a PayPal Developer SANDBOX REST app.
- GEMINI_API_KEY from Google AI Studio.
- GEMINI_MODEL defaults to gemini-3.8-flash.

Start the server:

~~~bash
uvicorn paypal_sentinel.app:app --host 127.0.0.1 --port 8000
~~~

Open http://127.0.0.1:8000.

## Sandbox-only controls
- Live PayPal mode is explicitly rejected.
- Client secret and Gemini key stay server-side and must never be committed.
- No production wallet or real payment is used.
- The PayPal buyer must approve the checkout.
- Orders and approvals are bound to stored server-side plans.
- Captures are checked against the approved amount and currency.
- A capture with an uncertain outcome is not automatically retried.

## Test

~~~bash
pytest -q
~~~

## Hackathon compliance and limitations
This is a newly created hackathon project. It uses the PayPal Developer Platform through the sandbox Orders v2 API and Gemini through the Gemini Developer API. It is a working prototype when sandbox credentials and a Gemini API key are configured. Do not claim production fraud detection, real funds, customer traction or revenue. The demo is not a substitute for PayPal's own risk systems.

The demo uses a fixed illustrative catalog and a sandbox merchant account configured by the entrant. No external merchant marketplace, multi-party settlement or production seller onboarding is implemented.

## License
MIT. See LICENSE in this directory.
