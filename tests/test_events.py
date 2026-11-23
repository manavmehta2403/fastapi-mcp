"""Comprehensive TDD tests for Event Subscriptions (@app.event) in v0.4.0."""

import asyncio
import time
from unittest.mock import patch
import pytest
from pydantic import BaseModel
from fastapi_mcp import FastAPIMCP, EventBroker


class PaymentAlert(BaseModel):
    """Test model for payment failure alerts."""
    transaction_id: str
    amount: float
    reason: str


@pytest.mark.asyncio
async def test_event_subscription_and_push():
    """Verify agent can subscribe to a topic and receive typed event payloads."""
    app = FastAPIMCP(auto_scan=False)
    handler_called = asyncio.Event()

    @app.event("billing.payment_failed")
    async def on_payment_failed(alert: PaymentAlert):
        assert alert.transaction_id == "tx_123"
        handler_called.set()

    queue = await app.subscribe_events("billing.payment_failed")

    delivered = await app.publish_event(
        "billing.payment_failed",
        PaymentAlert(transaction_id="tx_123", amount=49.99, reason="insufficient_funds"),
    )
    assert delivered == 1

    await asyncio.wait_for(handler_called.wait(), timeout=1.0)

    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received["topic"] == "billing.payment_failed"
    assert received["payload"]["transaction_id"] == "tx_123"
    assert received["payload"]["amount"] == 49.99


@pytest.mark.asyncio
async def test_wildcard_topic_matching():
    """Verify wildcard topic patterns match nested subtopics."""
    broker = EventBroker()

    q_all = await broker.subscribe("orders.*")
    q_other = await broker.subscribe("billing.*")

    await broker.publish("orders.created", {"order_id": "ord_1"})
    await broker.publish("orders.fulfilled", {"order_id": "ord_2"})
    await broker.publish("billing.invoice", {"invoice_id": "inv_1"})

    assert q_all.qsize() == 2
    assert q_other.qsize() == 1

    msg1 = await q_all.get()
    assert msg1["topic"] == "orders.created"

    msg2 = await q_all.get()
    assert msg2["topic"] == "orders.fulfilled"


@pytest.mark.asyncio
async def test_slow_consumer_backpressure_bounded_queue():
    """Verify bounded queue drops oldest event when slow consumer exceeds max_size."""
    broker = EventBroker(default_max_queue_size=2)
    q = await broker.subscribe("telemetry.cpu", max_queue_size=2)

    for i in range(5):
        await broker.publish("telemetry.cpu", {"step": i})

    assert q.qsize() == 2

    # Should retain the latest 2 events (steps 3 and 4)
    item1 = await q.get()
    assert item1["payload"]["step"] == 3
    item2 = await q.get()
    assert item2["payload"]["step"] == 4


@pytest.mark.asyncio
async def test_unsubscribe_and_cleanup():
    """Verify unsubscribing stops receiving events and close_all clears broker."""
    broker = EventBroker()
    q = await broker.subscribe("system.alerts")

    await broker.publish("system.alerts", {"msg": "warning 1"})
    assert q.qsize() == 1

    removed = await broker.unsubscribe("system.alerts", q)
    assert removed is True

    await broker.publish("system.alerts", {"msg": "warning 2"})
    assert q.qsize() == 1  # No new event received

    # Test close_all
    await broker.close_all()
    assert len(broker.list_topics()) == 0


@pytest.mark.asyncio
async def test_sync_handler_execution():
    """Verify synchronous event handlers run properly in threadpool executor."""
    app = FastAPIMCP(auto_scan=False)
    sync_done = False

    @app.event("metrics.sync")
    def on_sync_metric(data: dict):
        nonlocal sync_done
        time.sleep(0.02)
        sync_done = True

    await app.publish_event("metrics.sync", {"status": "ok"})
    await asyncio.sleep(0.08)
    assert sync_done is True


@pytest.mark.asyncio
async def test_list_topics_catalog():
    """Verify list_topics reflects all registered @app.event topics."""
    app = FastAPIMCP(auto_scan=False)

    @app.event("auth.login")
    async def on_login(payload: dict):
        pass

    @app.event("auth.logout")
    async def on_logout(payload: dict):
        pass

    topics = app.event_broker.list_topics()
    assert "auth.login" in topics
    assert "auth.logout" in topics


@pytest.mark.asyncio
async def test_event_broker_edge_cases():
    """Verify handler exceptions, non-existent unsubscribe, and queue race conditions."""
    broker = EventBroker()

    # Test non-existent unsubscribe
    dummy_q = asyncio.Queue()
    assert await broker.unsubscribe("none", dummy_q) is False

    # Test handler exception tolerance
    def bad_sync_handler(_payload):
        raise RuntimeError("boom")

    broker.register_topic("errors.sync", bad_sync_handler)
    delivered = await broker.publish("errors.sync", {"test": True})
    assert delivered == 0

    # Test async handler exception tolerance
    async def bad_async_handler(_payload):
        raise RuntimeError("boom")

    broker.register_topic("errors.async", bad_async_handler)
    delivered = await broker.publish("errors.async", {"test": True})
    assert delivered == 0

    # Test queue race conditions (QueueEmpty and QueueFull defensive branches)
    await broker.subscribe("race.topic", max_queue_size=1)
    sub = broker._subscriptions[-1]  # pylint: disable=protected-access
    await broker.publish("race.topic", {"item": 1})

    with patch.object(sub.queue, "get_nowait", side_effect=asyncio.QueueEmpty):
        await broker.publish("race.topic", {"item": 2})

    with patch.object(sub.queue, "put_nowait", side_effect=asyncio.QueueFull):
        await broker.publish("race.topic", {"item": 3})
