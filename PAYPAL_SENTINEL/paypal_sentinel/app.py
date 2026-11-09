from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai import AIPlannerError, parse_purchase_request
from .paypal import PayPalError, PayPalSandbox
from .policy import build_plan
from .storage import Store

app = FastAPI(title="PayPal Sentinel", version="0.1.0")
store = Store()
paypal = PayPalSandbox()
STATIC = Path(__file__).parent / "static"


class PlanRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)


class PlanResponse(BaseModel):
    plan_id: str
    sku: str
    quantity: int
    item_name: str
    amount: str
    currency: str
    decision: str
    reasons: list[str]
    rationale: str
    expires_in_seconds: int


class ApprovalRequest(BaseModel):
    plan_id: str = Field(min_length=8, max_length=100)


class OrderRequest(BaseModel):
    plan_id: str = Field(min_length=8, max_length=100)
    approval_token: str | None = Field(default=None, max_length=200)


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "sandbox-only", "real_funds": False}


@app.get("/api/config")
async def config():
    return {"paypal_client_id": os.getenv("PAYPAL_CLIENT_ID", ""), "currency": "USD"}


@app.post("/api/agent/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    try:
        ai_result = await parse_purchase_request(request.prompt)
        plan = build_plan(ai_result, request.prompt, store.daily_reserved())
        payload = {
            "sku": plan.sku,
            "quantity": plan.quantity,
            "item_name": plan.item_name,
            "unit_price": plan.unit_price,
            "amount": plan.amount,
            "currency": plan.currency,
            "risk_flags": list(plan.risk_flags),
            "decision": plan.decision,
            "reasons": list(plan.reasons),
            "rationale": plan.rationale,
            "intent_hash": plan.intent_hash,
        }
        plan_id = store.save_plan(payload)
        return PlanResponse(
            plan_id=plan_id,
            **{key: value for key, value in payload.items() if key != "intent_hash"},
            expires_in_seconds=600,
        )
    except AIPlannerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail="Policy or ledger validation failed safely") from exc


@app.post("/api/agent/approve")
async def approve_plan(request: ApprovalRequest):
    plan = store.get_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or expired")
    if plan["decision"] != "WARN":
        raise HTTPException(status_code=409, detail="Only WARN plans require manual approval")
    token = store.issue_approval(request.plan_id)
    return {"approval_token": token, "expires_in_seconds": 120, "intent_hash": plan["intent_hash"]}


@app.post("/api/paypal/orders")
async def create_paypal_order(request: OrderRequest):
    plan = store.get_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or expired")
    if plan["decision"] == "BLOCK":
        raise HTTPException(status_code=403, detail="Policy BLOCK: PayPal order creation refused")
    if plan["decision"] == "WARN":
        if not request.approval_token or not store.consume_approval(request.plan_id, request.approval_token):
            raise HTTPException(status_code=403, detail="A valid one-time approval is required")
    try:
        payment_id = store.reserve_payment(
            request.plan_id, plan["amount"], plan["currency"],
            os.getenv("DAILY_LIMIT_USD", "100.00"),
        )
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(status_code=403, detail="Daily spend reservation refused") from exc
    try:
        order = await paypal.create_order(
            plan["amount"], plan["currency"], request.plan_id, plan["item_name"], payment_id,
        )
        order_id = order["id"]
        store.set_order(payment_id, order_id)
        return {"id": order_id, "status": order.get("status", "CREATED"), "decision": plan["decision"]}
    except Exception as exc:
        store.fail_payment(payment_id)
        raise HTTPException(status_code=502, detail="PayPal sandbox order creation failed safely") from exc


@app.post("/api/paypal/orders/{order_id}/capture")
async def capture_paypal_order(order_id: str):
    payment = store.get_payment(order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Unknown PayPal order")
    if payment["state"] == "COMPLETED":
        return {"id": order_id, "status": "COMPLETED", "capture_id": payment["capture_id"]}
    if not store.begin_capture(order_id):
        raise HTTPException(
            status_code=409,
            detail="Order is not capturable or capture is already in progress; reconcile before retrying",
        )
    try:
        result = await paypal.capture_order(order_id)
        if result.get("status") != "COMPLETED":
            raise PayPalError("PayPal did not report COMPLETED")
        unit = result["purchase_units"][0]
        capture = unit["payments"]["captures"][0]
        captured_amount = capture["amount"]
        if captured_amount["currency_code"] != payment["currency"] or captured_amount["value"] != payment["amount"]:
            raise PayPalError("Captured amount does not match approved intent")
        store.complete_payment(order_id, capture["id"])
        return {"id": order_id, "status": "COMPLETED", "capture_id": capture["id"]}
    except Exception as exc:
        store.mark_capture_unknown(order_id)
        raise HTTPException(
            status_code=502,
            detail="Capture outcome is uncertain. Reconcile this order in PayPal before any retry.",
        ) from exc


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
