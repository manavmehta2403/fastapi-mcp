"""FastAPI integration with MCP server support."""

from contextlib import asynccontextmanager
import asyncio
import functools
import inspect
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
from mcp.server.mcpserver.exceptions import ToolError

from .scanner import RouteScanner, sanitize_tool_name
from .gateway import GatewayMode, BaseGatewayAdapter, setup_gateway_middleware
from .streaming import StreamToolSession, collect_stream
from .jobs import JobRegistry, execute_job_worker, register_job_meta_tools
from .events import EventBroker
from .webhooks import WebhookManager
from .protocols import ProtocolGateway
from .mesh import AgentMesh
from .webrtc import WebRTCManager
from .ui import setup_mcp_ui_routes


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
        gateway: Optional[BaseGatewayAdapter] = None,
        gateway_mode: GatewayMode = GatewayMode.HYBRID,
        job_ttl_seconds: float = 3600.0,
        max_completed_jobs: int = 1000,
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
        self.job_registry = JobRegistry(
            ttl_seconds=job_ttl_seconds,
            max_completed=max_completed_jobs,
        )
        self.event_broker = EventBroker()
        self.webhook_manager = WebhookManager()
        self.protocols = ProtocolGateway(self)
        self.gateways = self.protocols
        self.agent_mesh = AgentMesh(self)
        self.mesh = self.agent_mesh
        self.webrtc_manager = WebRTCManager(self)
        self.webrtc = self.webrtc_manager

        if session_context_provider:
            setattr(self._target_app, "_mcp_session_context_provider", session_context_provider)

        self.gateway = gateway
        self.gateway_mode = gateway_mode

        if self.gateway_mode == GatewayMode.MCP_ONLY:
            kwargs.setdefault("docs_url", None)
            kwargs.setdefault("redoc_url", None)
            kwargs.setdefault("openapi_url", None)

        if self.gateway_mode == GatewayMode.REST_ONLY:
            auto_scan = False

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

        unified_lifespan = self._create_lifespan(lifespan)

        if existing_app is None:
            super().__init__(*args, lifespan=unified_lifespan, **kwargs)
        else:
            if self.auto_scan:
                self.scan_routes()

        if self.gateway is not None:
            self._setup_gateway_middleware(self.gateway)

    def _create_lifespan(self, user_lifespan: Any) -> Any:
        @asynccontextmanager
        async def unified_lifespan(app: FastAPI):
            if self.auto_scan and not self._scanned:
                self.scan_routes()

            session_cm = None
            try:
                session_cm = self.mcp_server.session_manager.run()
            except (RuntimeError, AttributeError):
                pass

            try:
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
            finally:
                await self.job_registry.cancel_all()
                await self.event_broker.close_all()
                await self.webrtc_manager.close_all()

        return unified_lifespan

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

    def to_pydantic_ai_tools(
        self,
        names: Optional[List[str]] = None,
    ) -> List[Callable[..., Any]]:
        """Export registered MCP tools as native Pydantic AI agent tools.

        Returns callable tool runners with Pydantic v2 signatures compatible with
        `pydantic_ai.Agent(tools=[...])`.

        Args:
            names: Optional subset of tool names to export. If None, exports all tools.

        Returns:
            List of callable tool runners with Pydantic v2 type signatures.
        """
        catalog = self.get_tool_catalog()
        selected = names if names is not None else list(catalog.keys())
        return [catalog[name][2] for name in selected if name in catalog]

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
                    "is_streaming": getattr(runner, "_is_streaming", False),
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
                if getattr(runner, "_is_streaming", False):
                    stream_fn = getattr(runner, "_stream_func", runner)
                    return await collect_stream(stream_fn(**args))
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
            setattr(runner, "_is_dual_tool", True)
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
        required_scopes: Optional[List[str]] = None,
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

            if required_scopes and self.gateway:
                runner = self._wrap_scoped_runner(runner, name, required_scopes)

            setattr(runner, "_is_dual_tool", True)
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
            setattr(func, "_is_dual_tool", False)
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

    def stream_tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_buffer: int = 100,
        required_scopes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for streaming structured output tools returning async generators."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            s_name = sanitize_tool_name(name or func.__name__)
            s_doc = description or func.__doc__ or "Streaming tool returning incremental chunks."

            @functools.wraps(func)
            async def non_streaming_runner(*fn_args: Any, **fn_kwargs: Any) -> Dict[str, Any]:
                gen = func(*fn_args, **fn_kwargs)
                return await collect_stream(gen, max_items=max_buffer)

            non_streaming_runner.__annotations__["return"] = Dict[str, Any]
            setattr(non_streaming_runner, "__name__", s_name)
            setattr(non_streaming_runner, "__doc__", s_doc)
            setattr(non_streaming_runner, "_is_dual_tool", False)
            setattr(non_streaming_runner, "_is_streaming", True)
            setattr(non_streaming_runner, "_stream_func", func)

            runner_to_register: Callable[..., Any] = non_streaming_runner
            if required_scopes:
                runner_to_register = self._wrap_scoped_runner(
                    non_streaming_runner, s_name, required_scopes
                )
            self._tool_catalog[s_name] = (s_name, s_doc, runner_to_register)

            if not self.librarian:
                self.mcp_server.add_tool(
                    runner_to_register, name=s_name, description=s_doc, **kwargs
                )
                self._registered_tool_names.add(s_name)
            else:
                if self._scanned:
                    self._register_librarian_meta_tools()
            return func

        return decorator

    def call_stream_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        max_buffered: int = 100,
    ) -> StreamToolSession:
        """Call a registered streaming tool and return an active StreamToolSession."""
        if name not in self._tool_catalog:
            raise KeyError(f"Streaming tool '{name}' not found in catalog.")
        _, _, runner = self._tool_catalog[name]
        stream_fn = getattr(runner, "_stream_func", runner)
        args = arguments or {}
        gen = stream_fn(**args)
        return StreamToolSession(gen, max_buffered=max_buffered)

    def _register_job_meta_tools(self) -> None:
        """Register get_job_status and cancel_job meta tools once."""
        register_job_meta_tools(self)

    def job(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        timeout: Optional[float] = None,
        required_scopes: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for asynchronous long-running background jobs."""
        self._register_job_meta_tools()

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            j_name = sanitize_tool_name(name or func.__name__)
            j_doc = description or func.__doc__ or "Asynchronous background job."
            setattr(func, "_is_mcp_job", True)
            setattr(func, "_mcp_job_timeout", timeout)

            @functools.wraps(func)
            async def job_runner(*fn_args: Any, **fn_kwargs: Any) -> Dict[str, Any]:
                sig = inspect.signature(func)
                bound = sig.bind_partial(*fn_args, **fn_kwargs)
                bound.apply_defaults()
                job_state = await self.job_registry.create_job(tool_name=j_name)
                task = asyncio.create_task(
                    execute_job_worker(
                        job=job_state,
                        func=func,
                        args=bound.arguments,
                        timeout=timeout,
                    )
                )
                job_state.task = task
                return {
                    "job_id": job_state.job_id,
                    "status": "pending",
                    "message": "Job initiated in background.",
                }

            job_runner.__annotations__["return"] = Dict[str, Any]
            setattr(job_runner, "__name__", j_name)
            setattr(job_runner, "__doc__", j_doc)
            setattr(job_runner, "_is_dual_tool", False)
            setattr(job_runner, "_is_mcp_job", True)

            runner_to_register: Callable[..., Any] = job_runner
            if required_scopes:
                runner_to_register = self._wrap_scoped_runner(
                    job_runner, j_name, required_scopes
                )
            self._tool_catalog[j_name] = (j_name, j_doc, runner_to_register)

            if not self.librarian:
                self.mcp_server.add_tool(
                    runner_to_register, name=j_name, description=j_doc, **kwargs
                )
                self._registered_tool_names.add(j_name)
            else:
                if self._scanned:
                    self._register_librarian_meta_tools()
            return func

        return decorator

    def event(
        self,
        topic: str,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a handler callback for an event topic pattern."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.event_broker.register_topic(topic, func)
            return func

        return decorator

    async def publish_event(self, topic: str, payload: Any) -> int:
        """Publish an event to all matching subscribers and handlers."""
        return await self.event_broker.publish(topic, payload)

    async def subscribe_events(
        self,
        pattern: str,
        max_queue_size: Optional[int] = None,
    ) -> asyncio.Queue:
        """Subscribe to a topic pattern and return an event queue."""
        return await self.event_broker.subscribe(pattern, max_queue_size=max_queue_size)

    def webhook(
        self,
        path: str,
        *,
        secret: Optional[str] = None,
        secret_env: Optional[str] = None,
        header: str = "X-Hub-Signature-256",
        algorithm: str = "sha256",
        event_topic: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **route_kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register an inbound webhook endpoint with HMAC signature verification."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            wh_name = name or func.__name__
            wh_opts = {
                "secret": secret,
                "secret_env": secret_env,
                "header": header,
                "algorithm": algorithm,
                "event_topic": event_topic,
            }
            defn = self.webhook_manager.register(
                path=path,
                handler=func,
                name=wh_name,
                description=description or (func.__doc__ or "").strip(),
                **wh_opts,
            )
            endpoint_handler = self.webhook_manager.create_route_handler(defn)
            self._target_app.add_api_route(
                path,
                endpoint_handler,
                methods=["POST"],
                name=wh_name,
                description=defn.description,
                **route_kwargs,
            )
            return func

        return decorator

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """List all registered inbound webhooks and their configuration metadata."""
        return self.webhook_manager.list_webhooks()

    def mount_grpc(
        self,
        target: str,
        prefix: str,
        services: Optional[List[str]] = None,
        lazy: bool = True,
    ) -> List[str]:
        """Mount downstream gRPC service(s) as MCP tools via reflection or stub."""
        return self.protocols.mount_grpc(target, prefix, services=services, lazy=lazy)

    def mount_graphql(
        self,
        url: str,
        prefix: str,
        operations: Optional[List[str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        transport: Optional[Any] = None,
    ) -> List[str]:
        """Mount downstream GraphQL operations as MCP tools via introspection or query stub."""
        return self.protocols.mount_graphql(
            url,
            prefix,
            operations=operations,
            default_headers=default_headers,
            transport=transport,
        )

    def mount_remote(
        self,
        url: str,
        prefix: str,
        tools: Optional[List[str]] = None,
        token: Optional[str] = None,
        transport: Optional[Any] = None,
    ) -> List[str]:
        """Mount and namespace a remote MCP server cluster into the gateway catalog."""
        return self.agent_mesh.mount_remote(
            url=url, prefix=prefix, tools=tools, token=token, transport=transport
        )

    def webrtc_channel(
        self,
        name: str,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a handler for a named WebRTC DataChannel."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.webrtc_manager.register_channel(name, func)
            return func

        return decorator

    def mount_webrtc(self, path: str = "/mcp/webrtc") -> None:
        """Mount HTTP signaling endpoints for WebRTC peer connection offers/answers."""
        base = path.rstrip("/")

        @self.post(f"{base}/offer", include_in_schema=False)
        async def webrtc_offer(session_id: Optional[str] = None) -> Dict[str, Any]:
            return await self.webrtc_manager.create_offer(session_id=session_id)

        @self.post(f"{base}/answer", include_in_schema=False)
        async def webrtc_answer(req: Dict[str, Any]) -> Dict[str, Any]:
            sid = req.get("session_id", "")
            ans = req.get("sdp", "")
            return await self.webrtc_manager.process_answer(sid, ans)

    def _wrap_scoped_runner(
        self,
        runner: Callable[..., Any],
        tool_name: str,
        required_scopes: List[str],
    ) -> Callable[..., Any]:
        """Wrap tool runner with gateway scope authorization check."""
        @functools.wraps(runner)
        async def auth_guarded_runner(*args: Any, **kwargs: Any) -> Any:
            if self.gateway:
                headers: Dict[str, str] = {}
                provider: Any = (
                    getattr(self._target_app, "_mcp_session_context_provider", None)
                    or getattr(self, "session_context_provider", None)
                )
                if callable(provider):
                    caller = getattr(provider, "__call__", None)
                    if caller is not None:
                        try:
                            dyn_headers = caller(kwargs)
                        except TypeError:
                            dyn_headers = caller()
                        if isinstance(dyn_headers, dict):
                            headers = dyn_headers

                auth_ctx = await self.gateway.authenticate(headers)
                authorized = await self.gateway.authorize_tool(
                    tool_name, required_scopes, auth_ctx
                )
                if not authorized:
                    err_msg = (
                        f"Forbidden: caller lacks required scopes {required_scopes} "
                        f"for tool {tool_name}"
                    )
                    raise ToolError(err_msg)
            if inspect.iscoroutinefunction(runner):
                return await runner(*args, **kwargs)
            return runner(*args, **kwargs)

        return auth_guarded_runner

    def _setup_gateway_middleware(self, gateway: BaseGatewayAdapter) -> None:
        """Register gateway authentication and rate limiting middleware."""
        setup_gateway_middleware(self._target_app, gateway)

    def _setup_ui_routes(
        self,
        target_app: FastAPI,
        mcp_path: str = "/mcp",
        sse_path: str = "/sse",
    ) -> None:
        """Registers interactive MCP Swagger UI, ReDoc, and Studio endpoints."""
        setup_mcp_ui_routes(self, target_app=target_app, mcp_path=mcp_path, sse_path=sse_path)

    def mount_to(
        self,
        target_app: FastAPI,
        path: Optional[str] = "/mcp",
        sse_path: Optional[str] = "/sse",
        enable_ui: bool = True,
    ) -> None:
        """Mounts MCP transports (SSE and Streamable HTTP) onto another FastAPI app."""
        if self.gateway_mode == GatewayMode.REST_ONLY:
            return
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
        if self.gateway_mode == GatewayMode.REST_ONLY:
            return
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

    async def list_resources(self) -> List[Any]:
        """List all registered MCP resources."""
        return await self.mcp_server.list_resources()

    async def read_resource(self, uri: str) -> Any:
        """Read a registered MCP resource by URI."""
        return await self.mcp_server.read_resource(uri)

    async def list_prompts(self) -> List[Any]:
        """List all registered MCP prompts."""
        return await self.mcp_server.list_prompts()

    async def get_prompt(
        self, name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Get/render a registered MCP prompt by name and arguments."""
        return await self.mcp_server.get_prompt(name, arguments or {})

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a registered tool programmatically."""
        if not self._scanned and self.auto_scan:
            self.scan_routes()
        args = arguments or {}
        if self.librarian and name in self._tool_catalog:
            _, _, runner = self._tool_catalog[name]
            if getattr(runner, "_is_streaming", False):
                stream_fn = getattr(runner, "_stream_func", runner)
                return await collect_stream(stream_fn(**args))
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
