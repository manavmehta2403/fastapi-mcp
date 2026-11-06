"""Tests for Pydantic v2 and Pydantic AI integration."""

import inspect
import pytest
from pydantic import BaseModel
from fastapi_mcp import FastAPIMCP, StreamChunk


def test_stream_chunk_is_pydantic_v2_model():
    """Verify StreamChunk is a valid Pydantic v2 BaseModel with model_dump."""
    chunk = StreamChunk(chunk_id=1, data={"token": "test"}, is_last=True)
    assert isinstance(chunk, BaseModel)
    assert chunk.chunk_id == 1
    assert chunk.data == {"token": "test"}
    assert chunk.is_last is True
    dumped = chunk.model_dump()
    assert dumped["chunk_id"] == 1
    assert dumped["is_last"] is True


@pytest.mark.asyncio
async def test_to_pydantic_ai_tools_export():
    """Verify to_pydantic_ai_tools exports callable tools with Pydantic v2 signatures."""
    app = FastAPIMCP(auto_scan=False)

    class ItemQuery(BaseModel):
        item_id: str

    @app.api_tool("/items/query")
    async def query_item(item_id: str) -> dict:
        """Query item details."""
        return {"id": item_id, "found": True}

    tools = app.to_pydantic_ai_tools()
    assert len(tools) == 1
    runner = tools[0]

    assert callable(runner)
    assert runner.__name__ == "query_item"
    assert "Query item details" in runner.__doc__

    sig = inspect.signature(runner)
    assert "item_id" in sig.parameters

    res = await runner(item_id="item_42")
    assert res == {"id": "item_42", "found": True}


def test_to_pydantic_ai_tools_filter_by_name():
    """Verify to_pydantic_ai_tools can filter specific tools by name."""
    app = FastAPIMCP(auto_scan=False)

    @app.tool(name="alpha", description="Alpha tool")
    def alpha():
        return "alpha"

    @app.tool(name="beta", description="Beta tool")
    def beta():
        return "beta"

    tools_alpha = app.to_pydantic_ai_tools(names=["alpha"])
    assert len(tools_alpha) == 1
    assert tools_alpha[0].__name__ == "alpha"

    tools_none = app.to_pydantic_ai_tools(names=["non_existent"])
    assert len(tools_none) == 0
