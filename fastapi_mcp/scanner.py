import inspect
import re
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Tuple
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import Field
from pydantic_core import PydanticUndefined

from .dispatcher import ASGIDispatcher


def sanitize_tool_name(name: str) -> str:
    """Sanitize name to match MCP tool naming rules (alphanumeric, underscore, hyphen, max 64 chars)."""
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    if not clean:
        clean = "tool"
    return clean[:64]


class RouteScanner:
    """Scans and converts FastAPI routes into MCP tools."""

    def __init__(
        self,
        app: FastAPI,
        include_tags: Optional[Set[str]] = None,
        exclude_tags: Optional[Set[str]] = None,
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        include_methods: Optional[Set[str]] = None,
        headers_factory: Optional[Callable[[], Dict[str, str]]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        session_context_provider: Optional[Callable[[Dict[str, Any]], Dict[str, str]]] = None,
        enable_dry_run: bool = False,
        tool_name_prefix: str = "",
    ):
        self.app = app
        self.include_tags = set(include_tags) if include_tags else None
        self.exclude_tags = set(exclude_tags) if exclude_tags else set()
        self.include_paths = include_paths
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json"]
        self.include_methods = {
            m.upper() for m in (include_methods or {"GET", "POST", "PUT", "DELETE", "PATCH"})
        }
        self.headers_factory = headers_factory
        self.default_headers = default_headers
        self.session_context_provider = session_context_provider
        self.enable_dry_run = enable_dry_run
        self.tool_name_prefix = tool_name_prefix

    def should_include_route(self, route: APIRoute) -> bool:
        """Determines whether an APIRoute should be converted into an MCP tool."""
        # 1. Check path exclusions
        for exc in self.exclude_paths:
            if exc.endswith("*"):
                if route.path.startswith(exc[:-1]):
                    return False
            elif route.path == exc or route.path == exc.rstrip("/"):
                return False

        # 2. Check path inclusions if specified
        if self.include_paths:
            matched = False
            for inc in self.include_paths:
                if inc.endswith("*"):
                    if route.path.startswith(inc[:-1]):
                        matched = True
                        break
                elif route.path == inc:
                    matched = True
                    break
            if not matched:
                return False

        # 3. Check methods
        methods = {m.upper() for m in route.methods} & self.include_methods
        if not methods:
            return False

        # 4. Check tags
        route_tags = set(route.tags or [])
        if self.exclude_tags and (route_tags & self.exclude_tags):
            return False
        if self.include_tags is not None and not (route_tags & self.include_tags):
            return False

        return True

    def convert_route(self, route: APIRoute) -> Tuple[str, str, Callable]:
        """Converts an APIRoute into an MCP tool callable with signature and docstring."""
        methods = [m.upper() for m in route.methods if m.upper() in self.include_methods]
        method = methods[0] if methods else "GET"
        path_template = route.path
        dep = route.dependant

        raw_params: List[Tuple[str, Any, Any, bool]] = []
        annotations: Dict[str, Any] = {}

        # 1. Path parameters
        path_param_names: Set[str] = set()
        for p in dep.path_params:
            path_param_names.add(p.name)
            desc = getattr(p.field_info, "description", None)
            ann = Annotated[p.type_, Field(description=desc)] if desc else p.type_
            annotations[p.name] = ann
            raw_params.append((p.name, ann, inspect.Parameter.empty, True))

        # 2. Query parameters
        query_param_names: Set[str] = set()
        for p in dep.query_params:
            query_param_names.add(p.name)
            desc = getattr(p.field_info, "description", None)
            ann = Annotated[p.type_, Field(description=desc)] if desc else p.type_
            annotations[p.name] = ann
            default = p.field_info.default
            is_req = default is PydanticUndefined
            param_default = inspect.Parameter.empty if is_req else default
            raw_params.append((p.name, ann, param_default, is_req))

        # 3. Body parameters
        body_param_names: Set[str] = set()
        is_single_body_param = len(dep.body_params) == 1
        for p in dep.body_params:
            body_param_names.add(p.name)
            desc = getattr(p.field_info, "description", None)
            ann = Annotated[p.type_, Field(description=desc)] if desc else p.type_
            annotations[p.name] = ann
            default = p.field_info.default
            is_req = default is PydanticUndefined
            param_default = inspect.Parameter.empty if is_req else default
            raw_params.append((p.name, ann, param_default, is_req))

        # 4. Optional Dry-Run parameter for state-modifying actions
        is_state_modifying = method in {"POST", "PUT", "DELETE", "PATCH"}
        if self.enable_dry_run and is_state_modifying:
            dry_ann = Annotated[bool, Field(description="[Dry Run] If true, validates input and simulates action without writing changes")]
            annotations["dry_run"] = dry_ann
            raw_params.append(("dry_run", dry_ann, False, False))

        # Sort: required parameters first (is_req == True), then optional
        sorted_params = sorted(raw_params, key=lambda x: not x[3])

        parameters = [
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=ann,
                default=default,
            )
            for name, ann, default, is_req in sorted_params
        ]

        annotations["return"] = Any
        sig = inspect.Signature(parameters=parameters, return_annotation=Any)

        # Build tool name
        endpoint = route.endpoint
        raw_name = getattr(endpoint, "_mcp_tool_name", None) or route.operation_id or route.name
        if not raw_name or raw_name == "<lambda>":
            # Generate from method and path
            raw_name = f"{method.lower()}_{path_template}"
        tool_name = sanitize_tool_name(f"{self.tool_name_prefix}{raw_name}")

        # Build tool description
        endpoint_desc = getattr(endpoint, "_mcp_tool_description", None)
        summary = route.summary or ""
        doc = endpoint_desc or route.description or (endpoint.__doc__ if endpoint else "") or ""
        if summary and doc:
            tool_doc = f"[{method} {path_template}] {summary}\n\n{doc}"
        elif summary:
            tool_doc = f"[{method} {path_template}] {summary}"
        elif doc:
            tool_doc = f"[{method} {path_template}] {doc}"
        else:
            tool_doc = f"{method} request to {path_template}"

        # Create dispatcher runner
        dispatcher = ASGIDispatcher(
            app=self.app,
            method=method,
            path_template=path_template,
            path_param_names=path_param_names,
            query_param_names=query_param_names,
            body_param_names=body_param_names,
            is_single_body_param=is_single_body_param,
            headers_factory=self.headers_factory,
            default_headers=self.default_headers,
            session_context_provider=self.session_context_provider,
            enable_dry_run=self.enable_dry_run,
        )

        async def tool_runner(**kwargs: Any) -> Any:
            return await dispatcher(**kwargs)

        tool_runner.__name__ = tool_name
        tool_runner.__doc__ = tool_doc
        tool_runner.__signature__ = sig
        tool_runner.__annotations__ = annotations
        tool_runner._mcp_tags = list(route.tags or [])
        tool_runner._mcp_path = path_template
        tool_runner._mcp_method = method

        return tool_name, tool_doc, tool_runner

    def scan(self) -> List[Tuple[str, str, Callable]]:
        """Scans all routes on the FastAPI application and returns converted tool tuples."""
        tools = []
        registered_names: Set[str] = set()

        for route in self.app.routes:
            if isinstance(route, APIRoute) and self.should_include_route(route):
                name, doc, runner = self.convert_route(route)
                # Disambiguate if duplicate names occur
                base_name = name
                counter = 1
                while name in registered_names:
                    name = f"{base_name}_{counter}"
                    counter += 1
                registered_names.add(name)
                tools.append((name, doc, runner))

        return tools
