"""TDD verification test suite for all beta examples."""

import pytest


@pytest.mark.asyncio
async def test_example_gateway_auth():
    """Verify examples/gateway_auth.py runs successfully end-to-end."""
    from examples.gateway_auth import run_demo  # pylint: disable=import-outside-toplevel

    results = await run_demo()
    assert results["unauthorized_status"] == 401
    assert results["api_key_status"] == 200
    assert results["jwt_status"] == 200
    assert results["forbidden_status"] == 403
    assert results["rate_limited_status"] == 429


@pytest.mark.asyncio
async def test_example_streaming_and_jobs():
    """Verify examples/streaming_and_jobs.py runs successfully end-to-end."""
    from examples.streaming_and_jobs import run_demo  # pylint: disable=import-outside-toplevel

    results = await run_demo()
    assert results["stream_chunks_count"] == 3
    assert results["job_completed"] is True
    assert results["job_result"]["processed_items"] == 100


@pytest.mark.asyncio
async def test_example_events_and_webhooks():
    """Verify examples/events_and_webhooks.py runs successfully end-to-end."""
    from examples.events_and_webhooks import run_demo  # pylint: disable=import-outside-toplevel

    results = await run_demo()
    assert results["event_delivered"] is True
    assert results["webhook_status"] == 200
    assert results["webhook_tampered_status"] == 401
    assert results["webrtc_connected"] is True


@pytest.mark.asyncio
async def test_example_pydantic_ai_mesh():
    """Verify examples/pydantic_ai_mesh.py runs successfully end-to-end."""
    from examples.pydantic_ai_mesh import run_demo  # pylint: disable=import-outside-toplevel

    results = await run_demo()
    assert results["grpc_tool_invoked"] is True
    assert results["mesh_tool_invoked"] is True
    assert results["pydantic_ai_tools_count"] >= 2
    assert results["tool_execution_result"]["id"] == "item_99"


@pytest.mark.asyncio
async def test_example_dual_component_unified():
    """Verify examples/dual_component_unified.py runs successfully end-to-end."""
    from examples.dual_component_unified import run_demo  # pylint: disable=import-outside-toplevel

    results = await run_demo()
    assert results["rest_status"] == 200
    assert results["rest_title"] == "Enterprise AI Gateway Appliance"
    assert results["has_catalog_tool"] is True
    assert results["discount_qualified"] is True
    assert results["discount_savings"] == 99.80
    assert results["pydantic_ai_tools_count"] >= 2


@pytest.mark.asyncio
async def test_example_individual_component_decoupled():
    """Verify examples/individual_component_decoupled.py runs successfully end-to-end."""
    from examples.individual_component_decoupled import (  # pylint: disable=import-outside-toplevel
        run_demo,
    )

    results = await run_demo()
    assert results["headless_docs_status"] == 404
    assert results["headless_openapi_status"] == 404
    assert results["tool_cluster_id"] == "k8s-prod-us-east"
    assert results["tool_nodes_healthy"] == 18
    assert results["gateway_pass_status"] == 200
    assert results["gateway_rate_limited_status"] == 429
    assert results["has_retry_after_header"] is True
    assert results["obo_caller_type"] == "ai_agent"
    assert results["obo_agent_id"] == "autonomous-remediation-bot-9"
    assert results["obo_is_authenticated"] is True
