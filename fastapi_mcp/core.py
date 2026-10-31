import asyncio
from contextlib import asynccontextmanager
import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
)
from fastapi import FastAPI
from fastapi.datastructures import Default
from fastapi.routing import APIRoute
from mcp.server.mcpserver import MCPServer
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute

from .scanner import RouteScanner, sanitize_tool_name


class FastAPIMCP(FastAPI):
    """Unified FastAPI + FastMCP framework.

    Allows converting existing FastAPI routes to MCP tools automatically,
    defining dual REST + MCP tools with `@app.api_tool()`,
    or running pure MCP tools alongside standard REST routes.
    """

    def __init__(
        self,
        *args: Any,
        mcp_name: str = "FastAPIMCP",
        mcp_description: Optional[str] = None,
        auto_scan: bool = True,
        include_tags: Optional[Set[str]] = None,
        exclude_tags: Optional[Set[str]] = None,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        include_methods: Optional[Set[str]] = None,
        headers_factory: Optional[Callable[[], Dict[str, str]]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        tool_name_prefix: str = "",
        existing_app: Optional[FastAPI] = None,
        lifespan: Optional[Callable[[Any], Any]] = None,
        **kwargs: Any,
    ):
        self._target_app = existing_app or self
        self.mcp_name = mcp_name
        self.mcp_server = MCPServer(name=mcp_name, description=mcp_description)
        self.auto_scan = auto_scan
        self._scanned = False
        self._registered_tool_names: Set[str] = set()

        self.scanner = RouteScanner(
            app=self._target_app,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
            include_methods=include_methods,
            headers_factory=headers_factory,
            default_headers=default_headers,
            tool_name_prefix=tool_name_prefix,
        )

        # Custom lifespan to automatically scan routes on startup
        user_lifespan = lifespan

        @asynccontextmanager
        async def unified_lifespan(app: FastAPI):
            if self.auto_scan and not self._scanned:
                self.scan_routes()

            if user_lifespan is not None:
                async with user_lifespan(app) as maybe_state:
                    yield maybe_state
            else:
                yield

        if existing_app is None:
            super().__init__(*args, lifespan=unified_lifespan, **kwargs)
        else:
            # If wrapping an existing app, we can immediately scan existing routes
            if self.auto_scan:
                self.scan_routes()

    @classmethod
    def bind(
        cls,
        app: FastAPI,
        name: str = "FastAPIMCP",
        description: Optional[str] = None,
        auto_scan: bool = True,
        mount_path: Optional[str] = "/mcp",
        mount_sse_path: Optional[str] = "/sse",
        **kwargs: Any,
    ) -> "FastAPIMCP":
        """Factory method to bind FastMCP to an existing FastAPI instance in one line."""
        instance = cls(
            mcp_name=name,
            mcp_description=description,
            existing_app=app,
            auto_scan=auto_scan,
            **kwargs,
        )
        if mount_path or mount_sse_path:
            instance.mount_to(app, path=mount_path, sse_path=mount_sse_path)
        return instance

    def scan_routes(self) -> List[str]:
        """Scans the FastAPI app routes and registers matching routes as MCP tools."""
        tools = self.scanner.scan()
        added_names = []
        for name, doc, runner in tools:
            if name not in self._registered_tool_names:
                self.mcp_server.add_tool(runner, name=name, description=doc)
                self._registered_tool_names.add(name)
                added_names.append(name)
        self._scanned = True
        return added_names

    def api_tool(
        self,
        path: str,
        *,
        methods: Optional[List[str]] = None,
        tool_name: Optional[str] = None,
        tool_description: Optional[str] = None,
        **route_kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a function as BOTH a FastAPI REST route AND an MCP tool."""
        methods = [m.upper() for m in (methods or ["POST"])]

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            name = sanitize_tool_name(tool_name or func.__name__)
            doc = tool_description or func.__doc__ or f"{methods[0]} {path}"

            # Attach metadata to endpoint function
            func._mcp_tool_name = name
            func._mcp_tool_description = doc
            func._is_mcp_api_tool = True

            # 1. Register as FastAPI route on the application
            self._target_app.add_api_route(
                path=path,
                endpoint=func,
                methods=methods,
                **route_kwargs,
            )

            # 2. Register tool with scanner immediately
            if name not in self._registered_tool_names:
                route_matches = [
                    r for r in self._target_app.routes
                    if isinstance(r, APIRoute) and r.endpoint == func and r.path == path
                ]
                if route_matches:
                    _, _, runner = self.scanner.convert_route(route_matches[-1])
                    self.mcp_server.add_tool(runner, name=name, description=doc)
                    self._registered_tool_names.add(name)
                else:
                    self.mcp_server.add_tool(func, name=name, description=doc)
                    self._registered_tool_names.add(name)

            return func

        return decorator

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for pure MCP tools (like FastMCP's @mcp.tool()). Not exposed via REST."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            t_name = sanitize_tool_name(name or func.__name__)
            t_doc = description or func.__doc__
            self.mcp_server.add_tool(func, name=t_name, description=t_doc, **kwargs)
            self._registered_tool_names.add(t_name)
            return func

        return decorator

    def resource(self, *args: Any, **kwargs: Any) -> Callable:
        """Register an MCP resource."""
        return self.mcp_server.resource(*args, **kwargs)

    def prompt(self, *args: Any, **kwargs: Any) -> Callable:
        """Register an MCP prompt."""
        return self.mcp_server.prompt(*args, **kwargs)

    def _setup_ui_routes(
        self,
        target_app: FastAPI,
        mcp_path: str = "/mcp",
        sse_path: str = "/sse",
    ) -> None:
        """Registers the interactive MCP Swagger UI at {mcp_path}/docs and {mcp_path}/ui."""
        from pydantic import BaseModel
        from starlette.responses import HTMLResponse
        from .ui import get_mcp_swagger_html

        class ToolCallRequest(BaseModel):
            name: str
            arguments: Dict[str, Any] = {}

        docs_path = f"{mcp_path.rstrip('/')}/docs"
        ui_path = f"{mcp_path.rstrip('/')}/ui"
        call_path = f"{mcp_path.rstrip('/')}/ui/call"

        @target_app.get(docs_path, response_class=HTMLResponse, include_in_schema=False)
        @target_app.get(ui_path, response_class=HTMLResponse, include_in_schema=False)
        async def mcp_swagger_docs():
            tools = await self.list_tools()
            html = get_mcp_swagger_html(
                title=self.mcp_name,
                tools=tools,
                mcp_path=mcp_path,
                sse_path=sse_path,
                call_url=call_path,
            )
            return HTMLResponse(html)

        @target_app.post(call_path, include_in_schema=False)
        async def mcp_ui_call(req: ToolCallRequest):
            try:
                res = await self.call_tool(req.name, req.arguments)
                output_texts = [c.text for c in getattr(res, "content", []) if hasattr(c, "text")]
                output_str = "\n".join(output_texts) if output_texts else str(res)
                try:
                    import json
                    parsed_json = json.loads(output_str)
                    return {"success": True, "result": parsed_json}
                except Exception:
                    return {"success": True, "result": output_str}
            except Exception as e:
                return {"is_error": True, "error": str(e)}

    def mount_to(
        self,
        target_app: FastAPI,
        path: Optional[str] = "/mcp",
        sse_path: Optional[str] = "/sse",
        enable_ui: bool = True,
    ) -> None:
        """Mounts MCP transports (SSE and Streamable HTTP) onto another FastAPI app."""
        if enable_ui and path:
            self._setup_ui_routes(target_app, mcp_path=path, sse_path=sse_path or "/sse")

        if sse_path:
            target_app.mount(sse_path, self.mcp_server.sse_app())

        if path:
            target_app.mount(path, self.mcp_server.streamable_http_app())

    def mount_mcp(
        self,
        path: Optional[str] = "/mcp",
        sse_path: Optional[str] = "/sse",
        enable_ui: bool = True,
    ) -> None:
        """Mounts MCP transports directly onto self."""
        if enable_ui and path:
            self._setup_ui_routes(self, mcp_path=path, sse_path=sse_path or "/sse")

        if sse_path:
            super().mount(sse_path, self.mcp_server.sse_app())

        if path:
            super().mount(path, self.mcp_server.streamable_http_app())

    async def list_tools(self) -> List[Any]:
        """List all registered MCP tools."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        return await self.mcp_server.list_tools()

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a registered tool programmatically."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        return await self.mcp_server.call_tool(name, arguments or {})

    def run_stdio(self) -> None:
        """Run the MCP server over standard input/output (stdio).

        Ideal for Claude Desktop, Cursor, or local CLI agents without starting a network port.
        """
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        self.mcp_server.run(transport="stdio")

    async def run_stdio_async(self) -> None:
        """Async variant of run_stdio."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        await self.mcp_server.run_stdio_async()

    def run(self, transport: str = "stdio", **kwargs: Any) -> None:
        """Run the MCP server with the specified transport ('stdio', 'sse', 'streamable-http')."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        self.mcp_server.run(transport=transport, **kwargs)
