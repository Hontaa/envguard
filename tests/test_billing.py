import os

from billing import (
    mint_api_key,
    verify_lemonsqueezy_signature,
    handle_webhook_event,
)


def test_mint_api_key_format():
    key = mint_api_key()
    assert key.startswith("sk_")
    assert len(key) == 3 + 32  # sk_ + 16 bytes hex


def test_signature_verify_roundtrip():
    secret = "test_signing_secret"
    os.environ["LEMONSQUEEZY_SIGNING_SECRET"] = secret
    body = b'{"meta":{"event_name":"order_created"}}'
    import hmac, hashlib

    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_lemonsqueezy_signature(body, sig) is True
    assert verify_lemonsqueezy_signature(body, "deadbeef") is False
    assert verify_lemonsqueezy_signature(body, None) is False
    del os.environ["LEMONSQUEEZY_SIGNING_SECRET"]


def test_handle_webhook_mints_on_paid_event():
    key = handle_webhook_event("subscription_payment_success", {})
    assert key and key.startswith("sk_")


def test_handle_webhook_ignores_unknown():
    assert handle_webhook_event("subscription_cancelled", {}) is None
