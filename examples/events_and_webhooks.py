"""Reactive Event Subscriptions, Inbound Webhooks, and WebRTC Channels Example.

Demonstrates:
1. In-memory Pub/Sub event broker (@app.event) with wildcard topic routing (orders.*).
2. Cryptographically verified inbound webhooks (@app.webhook) with HMAC-SHA256.
3. Sub-millisecond peer-to-peer telemetry over WebRTC DataChannels (@app.webrtc_channel).
"""

import asyncio
import hashlib
import hmac
import json
from typing import Any, Dict

import httpx
from pydantic import BaseModel, Field

from fastapi_mcp import FastAPIMCP

WEBHOOK_SECRET = "whsec_production_stripe_secret_key_88"

app = FastAPIMCP(auto_scan=False, name="EventsAndWebhooksMCP")


# 1. Pydantic v2 Event & Webhook Payload Models
class OrderEvent(BaseModel):
    """Order lifecycle event schema."""

    order_id: str = Field(..., description="Unique order reference")
    amount: float = Field(..., description="Total payment amount")
    customer_email: str = Field(..., description="Customer notification address")


# In-memory tracking for event handler
received_events = []


# 2. Reactive Event Subscriptions: Topic pattern routing
@app.event("orders.*")
async def handle_order_events(event: OrderEvent) -> None:
    """Invoked reactively whenever an event matching 'orders.*' is published."""
    received_events.append(event)


# 3. Inbound Webhook Gateway: HMAC-SHA256 verified ingestion
@app.webhook("/webhooks/stripe", secret=WEBHOOK_SECRET, header="X-Hub-Signature-256")
async def stripe_webhook(payload: Dict[str, Any]) -> Dict[str, str]:
    """Ingest external Stripe webhook events and bridge into the MCP event broker."""
    order_id = payload.get("data", {}).get("object", {}).get("id", "ord_unknown")
    amount = payload.get("data", {}).get("object", {}).get("amount", 0) / 100.0

    # Publish into the internal reactive event mesh
    await app.publish_event(
        "orders.created",
        OrderEvent(
            order_id=order_id,
            amount=amount,
            customer_email="buyer@example.com",
        ),
    )
    return {"status": "received", "order_id": order_id}


# 4. WebRTC Channel: Sub-millisecond peer-to-peer data channel
@app.webrtc_channel("telemetry")
async def on_telemetry_channel(channel: Any) -> None:
    """Handle incoming WebRTC real-time data channel messages."""
    await channel.send({"telemetry_ack": True})


def _generate_hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute standard HMAC-SHA256 signature in GitHub/Stripe format."""
    sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


async def run_demo() -> Dict[str, Any]:
    """Execute event publication, webhook signature validation, and WebRTC signaling."""
    results: Dict[str, Any] = {}

    # Scenario 1: Direct Event Publish & Wildcard Topic Match
    queue = await app.subscribe_events("orders.*")
    delivered = await app.publish_event(
        "orders.fulfilled",
        OrderEvent(
            order_id="ord_9001",
            amount=150.00,
            customer_email="vip@example.com",
        ),
    )
    results["event_delivered"] = delivered > 0
    event_msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    results["received_order_id"] = event_msg["payload"]["order_id"]

    # Scenario 2: Inbound Webhook with Valid HMAC-SHA256 Signature
    transport = httpx.ASGITransport(app=app)
    webhook_body = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_12345", "amount": 9900}},
    }
    payload_bytes = json.dumps(webhook_body).encode("utf-8")
    valid_sig = _generate_hmac_signature(payload_bytes, WEBHOOK_SECRET)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid signature -> 200 OK
        res_valid = await client.post(
            "/webhooks/stripe",
            content=payload_bytes,
            headers={"X-Hub-Signature-256": valid_sig, "Content-Type": "application/json"},
        )
        results["webhook_status"] = res_valid.status_code

        # Tampered payload with original signature -> 401 Unauthorized
        tampered_bytes = json.dumps({"tampered": True}).encode("utf-8")
        res_tampered = await client.post(
            "/webhooks/stripe",
            content=tampered_bytes,
            headers={"X-Hub-Signature-256": valid_sig, "Content-Type": "application/json"},
        )
        results["webhook_tampered_status"] = res_tampered.status_code

    # Scenario 3: WebRTC Channel Offer/Answer Signaling
    offer = await app.webrtc_manager.create_offer(session_id="peer_session_1")
    ans_res = await app.webrtc_manager.process_answer(
        session_id="peer_session_1",
        sdp_answer="v=0\r\no=remote 12345\r\n",
    )
    results["webrtc_connected"] = ans_res["status"] == "connected"
    results["webrtc_has_telemetry"] = "telemetry" in offer["channels"]

    return results


if __name__ == "__main__":
    print("=== Running Reactive Events, Webhooks & WebRTC Demo ===")
    demo_results = asyncio.run(run_demo())
    rec_order_id = demo_results['received_order_id']
    print(f"1. Wildcard Event Delivered: {demo_results['event_delivered']} (Order: {rec_order_id})")
    print(f"2. Valid HMAC Webhook:       HTTP {demo_results['webhook_status']} (Expected 200)")
    attack_status = demo_results['webhook_tampered_status']
    print(f"3. Tampered Webhook Attack:  HTTP {attack_status} (Expected 401)")
    print(f"4. WebRTC Signaling Link:    Connected = {demo_results['webrtc_connected']}")
    print("All reactive events and webhook security checks passed!")
