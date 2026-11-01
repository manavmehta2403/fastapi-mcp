"""FastAPI integration with MCP server support."""

from contextlib import asynccontextmanager
import inspect
import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)
from fastapi import FastAPI
from fastapi.routing import APIRoute
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .scanner import RouteScanner, sanitize_tool_name
from .ui import (
    generate_mcp_openapi_spec,
    get_mcp_swagger_html,
    get_official_swagger_ui_html,
)


class ToolCallRequest(BaseModel):
    """Payload schema for executing MCP tools via the Swagger UI.

    Attributes:
        name: Name of the registered MCP tool to invoke.
        arguments: Dictionary of arguments matching the tool's input schema.
    """

    name: str
    arguments: Dict[str, Any] = {}


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
        session_context_provider: Optional[Callable[..., Dict[str, str]]] = None,
        enable_dry_run: bool = False,
        librarian: bool = False,
        tool_name_prefix: str = "",
        existing_app: Optional[FastAPI] = None,
        lifespan: Optional[Callable[[Any], Any]] = None,
        **kwargs: Any,
    ):
        """Initialize FastAPIMCP instance."""
        self._target_app = existing_app or self
        self.mcp_name = mcp_name
        self.mcp_server = MCPServer(name=mcp_name, description=mcp_description)
        self.auto_scan = auto_scan
        self._scanned = False
        self._registered_tool_names: Set[str] = set()
        self.librarian = librarian
        self.session_context_provider = session_context_provider
        self.enable_dry_run = enable_dry_run
        self._tool_catalog: Dict[str, Tuple[str, str, Callable]] = {}

        if session_context_provider:
            setattr(self._target_app, "_mcp_session_context_provider", session_context_provider)

        self.scanner = RouteScanner(
            app=self._target_app,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
            include_methods=include_methods,
            headers_factory=headers_factory,
            default_headers=default_headers,
            session_context_provider=session_context_provider,
            enable_dry_run=enable_dry_run,
            tool_name_prefix=tool_name_prefix,
        )

        user_lifespan = lifespan

        @asynccontextmanager
        async def unified_lifespan(app: FastAPI):
            if self.auto_scan and not self._scanned:
                self.scan_routes()

            session_cm = None
            try:
                session_cm = self.mcp_server.session_manager.run()
            except (RuntimeError, AttributeError):
                pass

            if session_cm is not None:
                async with session_cm:
                    if user_lifespan is not None:
                        async with user_lifespan(app) as maybe_state:
                            yield maybe_state
                    else:
                        yield
            else:
                if user_lifespan is not None:
                    async with user_lifespan(app) as maybe_state:
                        yield maybe_state
                else:
                    yield

        if existing_app is None:
            super().__init__(*args, lifespan=unified_lifespan, **kwargs)
        else:
            if self.auto_scan:
                self.scan_routes()

    @classmethod
    def bind(
        cls,
        app: FastAPI,
        *,
        name: str = "FastAPIMCP",
        description: Optional[str] = None,
        auto_scan: bool = True,
        mount_path: Optional[str] = "/mcp",
        mount_sse_path: Optional[str] = "/sse",
        librarian: bool = False,
        session_context_provider: Optional[Callable[..., Dict[str, str]]] = None,
        enable_dry_run: bool = False,
        **kwargs: Any,
    ) -> "FastAPIMCP":
        """Factory method to bind FastMCP to an existing FastAPI instance in one line."""
        instance = cls(
            mcp_name=name,
            mcp_description=description,
            existing_app=app,
            auto_scan=auto_scan,
            librarian=librarian,
            session_context_provider=session_context_provider,
            enable_dry_run=enable_dry_run,
            **kwargs,
        )
        if mount_path or mount_sse_path:
            instance.mount_to(app, path=mount_path, sse_path=mount_sse_path)
        return instance

    def set_session_context_provider(self, provider: Callable[..., Dict[str, str]]) -> None:
        """Sets or updates the dynamic session context provider callback."""
        self.session_context_provider = provider
        self.scanner.session_context_provider = provider
        setattr(self._target_app, "_mcp_session_context_provider", provider)

    def get_tool_catalog(self) -> Dict[str, Tuple[str, str, Callable]]:
        """Returns the dictionary of all discovered API tools in the catalog."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        return self._tool_catalog

    def _extract_param_schema(self, runner: Callable) -> Dict[str, Any]:
        """Extract parameter names, types, and defaults from a runner callable."""
        sig = getattr(runner, "__signature__", None)
        params_info: Dict[str, Any] = {}
        if not sig:
            return params_info

        for p_name, p in sig.parameters.items():
            if p.annotation != inspect.Parameter.empty:
                p_type = getattr(p.annotation, "__name__", str(p.annotation))
            else:
                p_type = "Any"

            is_req = p.default == inspect.Parameter.empty
            default_val = None if is_req else (
                str(p.default)
                if not isinstance(p.default, (int, float, bool, str, list, dict, type(None)))
                else p.default
            )
            params_info[p_name] = {
                "type": str(p_type),
                "required": is_req,
                "default": default_val,
            }
        return params_info

    def _register_librarian_meta_tools(self) -> None:
        """Registers the 3 Librarian meta-tools to prevent LLM context-window bloat."""
        if "_librarian_registered" in self._registered_tool_names:
            return

        async def list_api_categories() -> Dict[str, Any]:
            """List available API tool categories (tags) with tool counts and summaries."""
            categories: Dict[str, List[Dict[str, str]]] = {}
            for name, (_, t_doc, runner) in self._tool_catalog.items():
                tags = getattr(runner, "_mcp_tags", []) or ["default"]
                summary = (t_doc.split("\n")[0] if t_doc else "").strip()
                for tag in tags:
                    if tag not in categories:
                        categories[tag] = []
                    categories[tag].append({"name": name, "summary": summary})

            result = [
                {"category": cat, "tool_count": len(t_list), "tools": t_list}
                for cat, t_list in sorted(categories.items())
            ]
            hint = "Use 'search_api_tools(query, category)' to inspect parameter schemas."
            return {
                "categories": result,
                "total_tools": len(self._tool_catalog),
                "hint": hint,
            }

        async def search_api_tools(
            query: Optional[str] = None, category: Optional[str] = None
        ) -> Dict[str, Any]:
            """Search registered API tools by name, description, tags, or endpoint path."""
            matches = []
            q = (query or "").lower().strip()
            cat_filter = (category or "").lower().strip()

            for name, (_, t_doc, runner) in self._tool_catalog.items():
                tags = [t.lower() for t in getattr(runner, "_mcp_tags", []) or ["default"]]
                path = getattr(runner, "_mcp_path", "")
                method = getattr(runner, "_mcp_method", "")

                if cat_filter and not any(cat_filter in t for t in tags):
                    continue

                if q:
                    match_name = q in name.lower()
                    match_doc = q in (t_doc or "").lower()
                    match_path = q in path.lower()
                    match_tag = any(q in t for t in tags)
                    if not (match_name or match_doc or match_path or match_tag):
                        continue

                params_info = self._extract_param_schema(runner)
                matches.append({
                    "name": name,
                    "method": method,
                    "path": path,
                    "category": tags[0] if tags else "default",
                    "description": t_doc,
                    "parameters": params_info,
                })

            return {
                "tools": matches,
                "count": len(matches),
                "hint": "Call 'execute_api_tool(tool_name, arguments)' with required parameters.",
            }

        async def execute_api_tool(
            tool_name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> Any:
            """Execute an API tool discovered via search_api_tools by its name."""
            args = arguments or {}
            if tool_name not in self._tool_catalog:
                return {
                    "is_error": True,
                    "error": f"Tool '{tool_name}' not found in catalog.",
                    "available_tools": list(self._tool_catalog.keys())[:10],
                    "hint": "Call list_api_categories() or search_api_tools() for valid names.",
                }

            _, _, runner = self._tool_catalog[tool_name]
            try:
                if inspect.iscoroutinefunction(runner):
                    return await runner(**args)
                return runner(**args)
            except Exception as e:  # pylint: disable=broad-exception-caught
                return {
                    "is_error": True,
                    "tool_name": tool_name,
                    "error": str(e),
                }

        self.mcp_server.add_tool(
            list_api_categories,
            name="list_api_categories",
            description="List available API tool categories (tags) to prevent context bloat.",
        )
        self.mcp_server.add_tool(
            search_api_tools,
            name="search_api_tools",
            description="Search registered API tools by name, description, tags, or path.",
        )
        self.mcp_server.add_tool(
            execute_api_tool,
            name="execute_api_tool",
            description="Execute an API tool discovered via search_api_tools by its name.",
        )
        self._registered_tool_names.add("_librarian_registered")

    def scan_routes(self) -> List[str]:
        """Scans the FastAPI app routes and registers matching routes as MCP tools."""
        tools = self.scanner.scan()
        added_names = []
        for name, doc, runner in tools:
            self._tool_catalog[name] = (name, doc, runner)
            if not self.librarian:
                if name not in self._registered_tool_names:
                    self.mcp_server.add_tool(runner, name=name, description=doc)
                    self._registered_tool_names.add(name)
                    added_names.append(name)
            else:
                added_names.append(name)

        if self.librarian:
            self._register_librarian_meta_tools()

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

            setattr(func, "_mcp_tool_name", name)
            setattr(func, "_mcp_tool_description", doc)
            setattr(func, "_is_mcp_api_tool", True)
            setattr(func, "mcp_tool_name", name)
            setattr(func, "mcp_tool_description", doc)
            setattr(func, "is_mcp_api_tool", True)

            self._target_app.add_api_route(
                path=path,
                endpoint=func,
                methods=methods,
                **route_kwargs,
            )

            route_matches = [
                r for r in self._target_app.routes
                if isinstance(r, APIRoute) and r.endpoint == func and r.path == path
            ]
            if route_matches:
                _, _, runner = self.scanner.convert_route(route_matches[-1])
            else:
                runner = func

            self._tool_catalog[name] = (name, doc, runner)

            if not self.librarian:
                if name not in self._registered_tool_names:
                    self.mcp_server.add_tool(runner, name=name, description=doc)
                    self._registered_tool_names.add(name)
            else:
                if self._scanned:
                    self._register_librarian_meta_tools()

            return func

        return decorator

    def query(self, path: str, **kwargs: Any) -> Callable:
        """Route decorator for the modern HTTP QUERY method (RFC 10008)."""
        return self.api_route(path, methods=["QUERY"], **kwargs)

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for pure MCP tools (like FastMCP's @mcp.tool()). Not exposed via REST."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            t_name = sanitize_tool_name(name or func.__name__)
            t_doc = description or func.__doc__ or ""
            self._tool_catalog[t_name] = (t_name, t_doc, func)
            if not self.librarian:
                self.mcp_server.add_tool(func, name=t_name, description=t_doc, **kwargs)
                self._registered_tool_names.add(t_name)
            else:
                if self._scanned:
                    self._register_librarian_meta_tools()
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
        docs_path = f"{mcp_path.rstrip('/')}/docs"
        ui_path = f"{mcp_path.rstrip('/')}/ui"
        openapi_path = f"{mcp_path.rstrip('/')}/openapi.json"
        call_path = f"{mcp_path.rstrip('/')}/ui/call"
        tools_pattern = f"{mcp_path.rstrip('/')}/tools/{{tool_name}}"

        @target_app.get(openapi_path, include_in_schema=False)
        async def mcp_openapi_spec():
            tools = await self.list_tools()
            title = self.mcp_name + (" [Librarian Active]" if self.librarian else "")
            return generate_mcp_openapi_spec(
                title=title,
                tools=tools,
                mcp_path=mcp_path,
                catalog=self._tool_catalog,
            )

        @target_app.get(docs_path, response_class=HTMLResponse, include_in_schema=False)
        async def mcp_official_swagger():
            tools = await self.list_tools()
            title = self.mcp_name + (" [Librarian Active]" if self.librarian else "")
            spec = generate_mcp_openapi_spec(
                title=title,
                tools=tools,
                mcp_path=mcp_path,
                catalog=self._tool_catalog,
            )
            html = get_official_swagger_ui_html(
                title=f"{title} - MCP Swagger Explorer",
                openapi_url=openapi_path,
                spec=spec,
                mcp_path=mcp_path,
                sse_path=sse_path,
                ui_path=ui_path,
            )
            return HTMLResponse(html)

        @target_app.get(ui_path, response_class=HTMLResponse, include_in_schema=False)
        async def mcp_offline_ui():
            tools = await self.list_tools()
            title = self.mcp_name + (" [Librarian Active]" if self.librarian else "")
            html = get_mcp_swagger_html(
                title=title,
                tools=tools,
                mcp_path=mcp_path,
                sse_path=sse_path,
                call_url=call_path,
                docs_path=docs_path,
                openapi_path=openapi_path,
                ui_path=ui_path,
            )
            return HTMLResponse(html)

        @target_app.post(tools_pattern, include_in_schema=False)
        async def mcp_tool_direct_call(tool_name: str, request: Request):
            body: Dict[str, Any] = {}
            if request.headers.get("content-type", "").startswith("application/json"):
                try:
                    parsed = await request.json()
                    if isinstance(parsed, dict):
                        body = parsed
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
            try:
                res = await self.call_tool(tool_name, body)
                output_texts = [
                    c.text for c in getattr(res, "content", []) if hasattr(c, "text")
                ]
                output_str = "\n".join(output_texts) if output_texts else str(res)
                try:
                    parsed_json = json.loads(output_str)
                    return {"success": True, "result": parsed_json}
                except Exception:  # pylint: disable=broad-exception-caught
                    return {"success": True, "result": output_str}
            except Exception as e:  # pylint: disable=broad-exception-caught
                return JSONResponse(
                    status_code=400,
                    content={"is_error": True, "error": str(e)},
                )

        @target_app.post(call_path, include_in_schema=False)
        async def mcp_ui_call(req: ToolCallRequest):
            try:
                res = await self.call_tool(req.name, req.arguments)
                output_texts = [
                    c.text for c in getattr(res, "content", []) if hasattr(c, "text")
                ]
                output_str = "\n".join(output_texts) if output_texts else str(res)
                try:
                    parsed_json = json.loads(output_str)
                    return {"success": True, "result": parsed_json}
                except Exception:  # pylint: disable=broad-exception-caught
                    return {"success": True, "result": output_str}
            except Exception as e:  # pylint: disable=broad-exception-caught
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
            try:
                target_app.mount(sse_path, self.mcp_server.sse_app(sse_path="/"))
            except TypeError:
                target_app.mount(sse_path, self.mcp_server.sse_app())

        if path:
            try:
                target_app.mount(
                    path, self.mcp_server.streamable_http_app(streamable_http_path="/")
                )
            except TypeError:
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
            try:
                super().mount(sse_path, self.mcp_server.sse_app(sse_path="/"))
            except TypeError:
                super().mount(sse_path, self.mcp_server.sse_app())

        if path:
            try:
                super().mount(
                    path, self.mcp_server.streamable_http_app(streamable_http_path="/")
                )
            except TypeError:
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
        args = arguments or {}
        if self.librarian and name in self._tool_catalog:
            _, _, runner = self._tool_catalog[name]
            if inspect.iscoroutinefunction(runner):
                return await runner(**args)
            return runner(**args)
        return await self.mcp_server.call_tool(name, args)

    def run_stdio(self) -> None:
        """Run the MCP server over standard input/output (stdio)."""
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
