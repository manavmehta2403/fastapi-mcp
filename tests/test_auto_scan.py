import asyncio
from fastapi import FastAPI, Depends, Query, Path, Body
from pydantic import BaseModel, Field
import pytest
from fastapi_mcp import FastAPIMCP


def create_test_app():
    app = FastAPI(title="Store API")

    class Product(BaseModel):
        title: str = Field(..., description="Product title")
        price: float = Field(..., description="Product price")

    def get_database():
        return {"connection": "ok", "env": "test"}

    @app.get("/products/{product_id}", summary="Fetch single product")
    async def get_product(
        product_id: int = Path(..., description="Unique product ID"),
        include_reviews: bool = Query(False, description="Include product reviews"),
        db: dict = Depends(get_database),
    ):
        """Fetch full details of a specific product."""
        return {
            "id": product_id,
            "title": f"Product #{product_id}",
            "include_reviews": include_reviews,
            "db_status": db["connection"],
        }

    @app.post("/products", summary="Create new product")
    async def create_product(
        product: Product = Body(..., description="Product details"),
        category: str = Query("electronics", description="Product category"),
        db: dict = Depends(get_database),
    ):
        """Create a new product in the store."""
        return {
            "status": "created",
            "product": product.model_dump(),
            "category": category,
            "db_env": db["env"],
        }

    @app.get("/admin/metrics", tags=["internal"])
    async def admin_metrics():
        return {"cpu": 0.12, "memory": 0.45}

    return app


def test_auto_scan_and_invoke():
    app = create_test_app()
    # Bind FastMCP to the existing FastAPI app with admin path excluded
    mcp = FastAPIMCP.bind(
        app,
        name="StoreMCP",
        exclude_paths=["/admin/*", "/docs", "/redoc", "/openapi.json"],
    )

    # 1. Verify tools were discovered
    async def run_checks():
        tools = await mcp.list_tools()
        tool_names = [t.name for t in tools]
        print("Discovered tools:", tool_names)

        assert "get_product" in tool_names
        assert "create_product" in tool_names
        assert "admin_metrics" not in tool_names

        # 2. Check get_product schema
        get_tool = next(t for t in tools if t.name == "get_product")
        assert "product_id" in get_tool.input_schema["properties"]
        assert "include_reviews" in get_tool.input_schema["properties"]
        # Injected 'db' dependency must NOT be in input schema
        assert "db" not in get_tool.input_schema["properties"]
        assert get_tool.input_schema["required"] == ["product_id"]

        # 3. Call get_product tool
        res1 = await mcp.call_tool("get_product", {"product_id": 101, "include_reviews": True})
        assert res1.is_error is False
        assert "Product #101" in res1.content[0].text
        assert "db_status" in res1.content[0].text

        # 4. Call create_product tool
        res2 = await mcp.call_tool(
            "create_product",
            {
                "product": {"title": "Noise Cancelling Headphones", "price": 299.99},
                "category": "audio",
            },
        )
        assert res2.is_error is False
        assert "Noise Cancelling Headphones" in res2.content[0].text
        assert "audio" in res2.content[0].text
        assert "test" in res2.content[0].text

        print("test_auto_scan_and_invoke passed successfully!")

    asyncio.run(run_checks())


if __name__ == "__main__":
    test_auto_scan_and_invoke()
