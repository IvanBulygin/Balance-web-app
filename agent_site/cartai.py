"""
CartAI integration — AI agent that completes third-party checkouts.

Scope: TEST MODE ONLY.
Uses CartAI's documented sandbox card (4242 4242 4242 4242, expiry 12/2034,
cvv 444) via ``payment.provider="test"``. No real card data flows through this
service. Going to a real-card flow would put us in PCI-DSS scope, which we
have not committed to — that's intentional.

Reads ``CARTAI_API_KEY`` from env at call time (set it in the Render dashboard
under Service → Environment — never inline in code or chat). When the key is
absent the routes return 503 with a clear message rather than crashing.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, EmailStr, Field

CARTAI_BASE = "https://api.cartai.ai"
HTTP_TIMEOUT_S = 30.0

# Documented sandbox card from CartAI's "Sharing a Test Link" docs. The real
# transaction is simulated — never replace this with a real PAN unless and
# until we have a card vault / tokenization story.
_SANDBOX_PAYMENT = {
    "provider": "test",
    "data": {
        "name": "Test Buyer",
        "cardNumber": "4242424242424242",
        "expiryYear": "2034",
        "expiryMonth": "12",
        "cvv": "444",
    },
}


class CheckoutItem(BaseModel):
    url: str
    quantity: int = Field(1, ge=1, le=10)
    selectedVariant: Optional[dict] = None
    metadata: Optional[dict] = None


class CheckoutAddress(BaseModel):
    addressLine1: str
    addressLine2: str = ""
    city: str
    province: str  # two-letter US state code, e.g. "NY"
    postalCode: str
    country: str = "US"


class CheckoutContact(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    phone: str


class CheckoutRequest(BaseModel):
    contact: CheckoutContact
    address: CheckoutAddress
    items: list[CheckoutItem] = Field(..., min_length=1)


def is_enabled() -> bool:
    """Cheap probe the UI uses to know whether to show the Buy button."""
    return bool(os.environ.get("CARTAI_API_KEY"))


def _client() -> httpx.Client:
    key = os.environ.get("CARTAI_API_KEY")
    if not key:
        raise RuntimeError(
            "CARTAI_API_KEY is not set. Add it to the Render dashboard "
            "(Service → Environment) so the backend can call CartAI."
        )
    return httpx.Client(
        base_url=CARTAI_BASE,
        headers={"X-Api-Key": key, "Content-Type": "application/json"},
        timeout=HTTP_TIMEOUT_S,
    )


def create_checkout(req: CheckoutRequest) -> dict[str, Any]:
    """POST /checkout — returns CartAI's response, including a ``taskId``."""
    body = {
        "customer": {
            "contact": req.contact.model_dump(),
            "shippingAddress": req.address.model_dump(),
            "billingAddress": req.address.model_dump(),
            "shippingMethod": {"strategy": "cheapest"},
            "payment": _SANDBOX_PAYMENT,
        },
        "tasks": [t.model_dump(exclude_none=True) for t in req.items],
        "options": {
            "verifyBeforePlacement": False,
            "failTaskIfNotConfirmed": False,
            "allowPartialCheckoutForMultiSku": True,
        },
    }
    with _client() as client:
        r = client.post("/checkout", json=body)
        r.raise_for_status()
        return r.json()


def get_checkout(task_id: str) -> dict[str, Any]:
    """GET /checkout/{taskId} — current state of an in-flight task."""
    with _client() as client:
        r = client.get(f"/checkout/{task_id}")
        r.raise_for_status()
        return r.json()
