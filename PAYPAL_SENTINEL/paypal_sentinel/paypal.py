from __future__ import annotations

import os
import time

import httpx


class PayPalError(RuntimeError):
    pass


class PayPalSandbox:
    BASE_URL = "https://api-m.sandbox.paypal.com"

    def __init__(self):
        if os.getenv("PAYPAL_MODE", "sandbox").lower() != "sandbox":
            raise PayPalError("This hackathon build is sandbox-only; live mode is disabled")
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self._token: str | None = None
        self._token_expiry = 0

    async def access_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise PayPalError("PayPal sandbox credentials are not configured")
        if self._token and time.time() < self._token_expiry - 30:
            return self._token
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.BASE_URL + "/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 300))
        return self._token

    async def create_order(
        self, amount: str, currency: str, plan_id: str, description: str, request_id: str
    ) -> dict:
        token = await self.access_token()
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": plan_id,
                "custom_id": plan_id,
                "description": description[:120],
                "amount": {"currency_code": currency, "value": amount},
            }],
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.BASE_URL + "/v2/checkout/orders",
                json=body,
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": request_id,
                },
            )
            response.raise_for_status()
            return response.json()

    async def capture_order(self, order_id: str) -> dict:
        token = await self.access_token()
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.BASE_URL + "/v2/checkout/orders/" + order_id + "/capture",
                json={},
                headers={
                    "Authorization": "Bearer " + token,
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": order_id + "-capture",
                },
            )
            response.raise_for_status()
            return response.json()
