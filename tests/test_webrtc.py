"""Comprehensive TDD tests for WebRTC Real-Time Agent Channels in v0.8.0."""

import pytest
from starlette.testclient import TestClient
from fastapi_mcp import FastAPIMCP, WebRTCChannelSession, WebRTCManager


@pytest.mark.asyncio
async def test_webrtc_signaling_offer_and_answer():
    """Verify offer generation and answer processing establish active channels."""
    app = FastAPIMCP(auto_scan=False)

    @app.webrtc_channel("telemetry")
    async def on_telemetry(channel):
        pass

    offer = await app.webrtc_manager.create_offer(session_id="peer_101")
    assert offer["session_id"] == "peer_101"
    assert "telemetry" in offer["channels"]
    assert "v=0" in offer["sdp"]

    # Process SDP answer
    ans_res = await app.webrtc_manager.process_answer(
        session_id="peer_101", sdp_answer="v=0\r\no=remote\r\n"
    )
    assert ans_res["status"] == "connected"

    # Verify session is created
    sess = await app.webrtc_manager.get_channel_session("peer_101", "telemetry")
    assert sess is not None
    assert sess.state == "open"


@pytest.mark.asyncio
async def test_webrtc_datachannel_send_and_receive():
    """Verify bidirectional message passing over WebRTCChannelSession."""
    sess = WebRTCChannelSession(session_id="peer_202", channel_name="vision")
    assert sess.state == "open"

    await sess.send({"frame_id": 1, "status": "tracking"})
    outbound = await sess._outbound_queue.get()
    assert outbound["frame_id"] == 1

    await sess.post_inbound({"command": "recalibrate"})
    inbound = await sess.receive()
    assert inbound["command"] == "recalibrate"


@pytest.mark.asyncio
async def test_webrtc_channel_closed_error_handling():
    """Verify sending on closed channel raises ConnectionError."""
    sess = WebRTCChannelSession(session_id="peer_303", channel_name="audio")
    await sess.close()
    assert sess.state == "closed"

    with pytest.raises(ConnectionError, match="is closed"):
        await sess.send("audio_packet")

    with pytest.raises(ConnectionError, match="is closed"):
        await sess.receive()


def test_webrtc_http_signaling_endpoints():
    """Verify HTTP signaling endpoints /mcp/webrtc/offer and /answer work with TestClient."""
    app = FastAPIMCP(auto_scan=False)

    @app.webrtc_channel("chat")
    async def on_chat(ch):
        pass

    app.mount_webrtc(path="/mcp/webrtc")

    with TestClient(app) as client:
        r_offer = client.post("/mcp/webrtc/offer")
        assert r_offer.status_code == 200
        offer_data = r_offer.json()
        assert "session_id" in offer_data
        assert "chat" in offer_data["channels"]

        sid = offer_data["session_id"]
        r_ans = client.post("/mcp/webrtc/answer", json={"session_id": sid, "sdp": "v=0\r\n"})
        assert r_ans.status_code == 200
        assert r_ans.json()["status"] == "connected"

        # Invalid answer
        r_invalid = client.post("/mcp/webrtc/answer", json={"session_id": sid, "sdp": ""})
        assert r_invalid.json().get("is_error") is True


@pytest.mark.asyncio
async def test_webrtc_lifespan_close_all():
    """Verify manager close_all gracefully terminates active peer sessions."""
    app = FastAPIMCP(auto_scan=False)

    @app.webrtc_channel("control")
    async def on_control(ch):
        pass

    await app.webrtc_manager.process_answer("peer_505", "v=0\r\n")
    sess = await app.webrtc_manager.get_channel_session("peer_505", "control")
    assert sess is not None

    await app.webrtc_manager.close_all()
    assert sess.state == "closed"
