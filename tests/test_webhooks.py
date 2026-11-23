"""Tests for Inbound Webhook Gateway and HMAC signature verification."""

import hashlib
import hmac
import json
import os
from typing import Any
import httpx
import pytest
from fastapi_mcp import FastAPIMCP, verify_hmac_signature
from fastapi_mcp.webhooks import WebhookManager


def test_verify_hmac_signature_algorithms_and_formats():
    secret = "super_secret_webhook_key"
    payload = b'{"event": "charge.succeeded", "amount": 4200}'

    # 1. Standard SHA-256 raw hex
    sig_sha256 = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert verify_hmac_signature(payload, secret, sig_sha256, "sha256") is True

    # 2. GitHub prefix 'sha256='
    assert verify_hmac_signature(payload, secret, f"sha256={sig_sha256}", "sha256") is True

    # 3. SHA-1 format
    sig_sha1 = hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest()
    assert verify_hmac_signature(payload, secret, f"sha1={sig_sha1}", "sha1") is True

    # 4. Stripe timestamped signature t=...,v1=...
    ts = "1700000000"
    ts_payload = f"{ts}.".encode("utf-8") + payload
    v1_sig = hmac.new(secret.encode(), ts_payload, hashlib.sha256).hexdigest()
    stripe_header = f"t={ts},v1={v1_sig}"
    assert verify_hmac_signature(payload, secret, stripe_header, "sha256") is True

    # 5. Tampered payload
    tampered_payload = b'{"event": "charge.succeeded", "amount": 9999}'
    assert verify_hmac_signature(tampered_payload, secret, sig_sha256, "sha256") is False

    # 6. Wrong secret
    assert verify_hmac_signature(payload, "wrong_secret", sig_sha256, "sha256") is False

    # 7. Empty or missing values
    assert verify_hmac_signature(payload, "", sig_sha256) is False
    assert verify_hmac_signature(payload, secret, "") is False
    assert verify_hmac_signature(payload, secret, sig_sha256, "nonexistent_algo") is False

    # 8. String payload
    assert (
        verify_hmac_signature(
            '{"test": true}',
            secret,
            hmac.new(secret.encode(), b'{"test": true}', hashlib.sha256).hexdigest(),
        )
        is True
    )


@pytest.mark.asyncio
async def test_webhook_route_post_validation_and_rejection():
    app = FastAPIMCP(auto_scan=False)
    secret = "whsec_github_token_xyz"
    received_events = []

    @app.webhook(
        "/api/webhooks/github",
        secret=secret,
        header="X-Hub-Signature-256",
        algorithm="sha256",
        name="github_push_handler",
        description="Handles GitHub push events",
    )
    async def on_github_push(payload: Any):
        received_events.append(payload)
        ref = payload.get("ref") if isinstance(payload, dict) else None
        return {"processed": True, "ref": ref}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload_data = {"ref": "refs/heads/main", "commits": 1}
        raw_body = json.dumps(payload_data).encode("utf-8")

        # 1. Missing signature header -> 401
        res = await client.post(
            "/api/webhooks/github",
            content=raw_body,
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code == 401
        assert "Missing required webhook signature header" in res.json()["detail"]

        # 2. Invalid signature header -> 401
        res = await client.post(
            "/api/webhooks/github",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalidhexsignature0000000",
            },
        )
        assert res.status_code == 401
        assert res.json()["detail"] == "Invalid webhook signature"

        # 3. Valid signature header -> 200 OK
        valid_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        res = await client.post(
            "/api/webhooks/github",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={valid_sig}",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "accepted"
        assert data["webhook"] == "github_push_handler"
        assert data["result"] == {"processed": True, "ref": "refs/heads/main"}
        assert len(received_events) == 1

        # 4. Invalid JSON payload with application/json header fallback
        invalid_json_body = b"not-a-valid-json-string{["
        invalid_json_sig = hmac.new(secret.encode(), invalid_json_body, hashlib.sha256).hexdigest()
        res_malformed = await client.post(
            "/api/webhooks/github",
            content=invalid_json_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": invalid_json_sig,
            },
        )
        assert res_malformed.status_code == 200


@pytest.mark.asyncio
async def test_webhook_secret_env_and_unauthenticated_flow():
    os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_live_998877"
    app = FastAPIMCP(auto_scan=False)

    @app.webhook(
        "/api/webhooks/stripe",
        secret_env="STRIPE_WEBHOOK_SECRET",
        header="Stripe-Signature",
        name="stripe_receiver",
    )
    def on_stripe_event(payload: dict):
        return {"received_id": payload.get("id")}

    @app.webhook(
        "/api/webhooks/public",
        name="public_receiver",
    )
    def on_public_event(payload: Any):
        return {"public_status": "ok", "type": type(payload).__name__}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test env secret resolution
        raw_body = json.dumps({"id": "evt_123"}).encode("utf-8")
        sig = hmac.new(b"whsec_live_998877", raw_body, hashlib.sha256).hexdigest()

        res = await client.post(
            "/api/webhooks/stripe",
            content=raw_body,
            headers={"Content-Type": "application/json", "Stripe-Signature": sig},
        )
        assert res.status_code == 200
        assert res.json()["result"]["received_id"] == "evt_123"

        # Test unauthenticated webhook without secret configured
        res_pub = await client.post(
            "/api/webhooks/public",
            json={"open": True},
        )
        assert res_pub.status_code == 200
        assert res_pub.json()["result"]["public_status"] == "ok"

        # Test non-json payload handling
        res_raw = await client.post(
            "/api/webhooks/public",
            content=b"RAW_DATA_STREAM",
            headers={"Content-Type": "text/plain"},
        )
        assert res_raw.status_code == 200

        # Trigger history trimming (> 100 entries)
        for _ in range(105):
            await client.post("/api/webhooks/public", json={"ping": True})
        assert len(app.webhook_manager._delivery_history) == 100


@pytest.mark.asyncio
async def test_webhook_manager_simulation_and_metadata():
    mgr = WebhookManager()

    def sync_wh(payload: Any):
        if isinstance(payload, dict):
            return {"sync": True, "keys": list(payload.keys())}
        return {"sync": True, "raw": payload}

    async def async_wh(payload: dict):
        return {"async": True, "count": len(payload)}

    defn1 = mgr.register("/sync", sync_wh, secret="sec1", name="sync_hook")
    defn2 = mgr.register("/async", async_wh, secret="sec2", name="async_hook")
    defn_no_sec = mgr.register("/no-sec", sync_wh, name="no_sec_hook")
    defn_no_handler = mgr.register("/no-handler", None, name="no_handler_hook")

    assert defn1.name == "sync_hook"
    assert defn2.name == "async_hook"
    assert mgr.get_webhook("/sync") is defn1
    assert mgr.get_webhook("/missing") is None

    # Simulate deliveries
    res1 = await mgr.simulate_delivery("/sync", {"alpha": 1, "beta": 2})
    assert res1["result"] == {"sync": True, "keys": ["alpha", "beta"]}

    res2 = await mgr.simulate_delivery(
        "/async", {"x": 10}, secret="override_sec", custom_headers={"X-Test": "1"}
    )
    assert res2["result"] == {"async": True, "count": 1}

    # Simulation with string / bytes
    res3 = await mgr.simulate_delivery("/sync", "raw_string")
    assert res3["status"] == "accepted"

    # Simulation without secret
    res_no_sec = await mgr.simulate_delivery("/no-sec", {"val": 1})
    assert res_no_sec["status"] == "accepted"

    # Simulation without handler
    res_no_h = await mgr.simulate_delivery("/no-handler", {"val": 2})
    assert res_no_h["result"] is None

    # Missing path simulation raises KeyError
    with pytest.raises(KeyError):
        await mgr.simulate_delivery("/not_found", {})

    # Metadata export
    exported = mgr.list_webhooks()
    assert len(exported) == 4
    names = [h["name"] for h in exported]
    assert "sync_hook" in names
    assert "no_handler_hook" in names


def test_app_list_webhooks():
    app = FastAPIMCP(auto_scan=False)

    @app.webhook("/hook1", name="first_hook")
    def hook1(p): return p

    @app.webhook("/hook2", name="second_hook", secret="s2")
    def hook2(p): return p

    hooks = app.list_webhooks()
    assert len(hooks) == 2
    names = {h["name"] for h in hooks}
    assert "first_hook" in names
    assert "second_hook" in names
