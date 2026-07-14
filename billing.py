"""Billing layer for envguard SaaS.

Supports Lemon Squeezy as the payment provider (Merchant of Record —
handles VAT/tax, no business entity required). Stripe variant is stubbed
for later.

Flow:
  1. Client hits POST /v1/checkout -> we return a Lemon Squeezy checkout URL.
  2. User pays -> Lemon Squeezy POSTs a signed webhook to /webhooks/lemonsqueezy.
  3. We verify the HMAC signature, then mint an API key and store it in the
     drift DB's `api_keys` table. The key then unlocks /v1/scan and /v1/drift.

All secrets come from environment variables (never hardcoded):
  LEMONSQUEEZY_API_KEY        - from Lemon Squeezy > Settings > API
  LEMONSQUEEZY_SIGNING_SECRET - from Store > Settings > Webhooks
  LEMONSQUEEZY_STORE_ID       - numeric store id
  LEMONSQUEEZY_PRODUCT_ID     - the paid plan product id
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

import httpx


def mint_api_key() -> str:
    """Generate a new API key (sk_...)."""
    return "sk_" + secrets.token_hex(16)


def verify_lemonsqueezy_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verify the X-Signature HMAC-SHA256 from Lemon Squeezy.

    Lemon Squeezy computes: HMAC_SHA256(signing_secret, raw_request_body).
    """
    secret = os.environ.get("LEMONSQUEEZY_SIGNING_SECRET", "")
    if not secret or not signature_header:
        return False
    expected = hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def create_checkout(redirect_url: str = "") -> dict:
    """Create a Lemon Squeezy checkout session and return its URL.

    Returns dict with keys: ok, checkout_url, error.
    """
    api_key = os.environ.get("LEMONSQUEEZY_API_KEY")
    store_id = os.environ.get("LEMONSQUEEZY_STORE_ID")
    product_id = os.environ.get("LEMONSQUEEZY_PRODUCT_ID")
    if not (api_key and store_id and product_id):
        return {"ok": False, "error": "billing not configured (missing env vars)"}

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "product_id": int(product_id),
                "redirect_url": redirect_url or os.environ.get("APP_URL", ""),
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(store_id)}}
            },
        }
    }
    try:
        r = httpx.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            timeout=15,
        )
        if r.status_code >= 400:
            return {"ok": False, "error": f"Lemon Squeezy {r.status_code}: {r.text[:200]}"}
        data = r.json()["data"]
        return {
            "ok": True,
            "checkout_url": data["attributes"]["url"],
        }
    except Exception as e:  # network / parse errors
        return {"ok": False, "error": f"request failed: {e}"}


def handle_webhook_event(event_name: str, meta: dict) -> Optional[str]:
    """React to a Lemon Squeezy webhook event.

    On a successful subscription/payment, mint and return a new API key.
    Returns the key string, or None if no key should be minted.
    """
    positive_events = {
        "subscription_created",
        "subscription_payment_success",
        "order_created",
        "license_key_created",
    }
    if event_name in positive_events:
        return mint_api_key()
    return None
