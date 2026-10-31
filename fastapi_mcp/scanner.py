"""Route scanner and conversion engine for FastAPI-MCP.

Inspects FastAPI application routes, extracts path/query/body parameters,
preserves Pydantic schemas, and generates compliant Model Context Protocol (MCP) tools.
"""

import inspect
import re
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Tuple
from fastapi import FastAPI
from fastapi.routing import APIRoute
from pydantic import Field
from pydantic_core import PydanticUndefined

from .dispatcher import ASGIDispatcher


def sanitize_tool_name(name: str) -> str:
    """Sanitize name to match MCP tool naming rules (alphanumeric, underscore, hyphen, <=64).

    Args:
        name: Raw identifier or path string.

    Returns:
        Sanitized tool name matching MCP specifications.
    """
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    if not clean:
        clean = "tool"
    return clean[:64]


def _extract_param_type(param: Any) -> Any:
    """Extract Python type annotation from FastAPI / Pydantic param across v1 and v2.

    Args:
        param: Dependant parameter object.

    Returns:
        Resolved Python type annotation or Any.
    """
    field_info = getattr(param, "field_info", None)
    if field_info is not None:
        ann = getattr(field_info, "annotation", None)
        if ann is not None and ann is not PydanticUndefined:
            return ann
    if getattr(param, "annotation", None) is not None:
        return param.annotation
    if hasattr(param, "type_"):
        return param.type_
    return Any


def _collect_dependant_params(
    params_list: List[Any],
    annotations: Dict[str, Any],
    is_path_param: bool = False,
) -> Tuple[Set[str], List[Tuple[str, Any, Any, bool]]]:
    """Helper to collect parameters and their type annotations from route dependant."""
    param_names: Set[str] = set()
    raw_params: List[Tuple[str, Any, Any, bool]] = []

    for p in params_list:
        param_names.add(p.name)
        desc = getattr(p.field_info, "description", None)
        p_type = _extract_param_type(p)
        ann = Annotated[p_type, Field(description=desc)] if desc else p_type
        annotations[p.name] = ann

        if is_path_param:
            raw_params.append((p.name, ann, inspect.Parameter.empty, True))
        else:
            default = p.field_info.default
            is_req = default is PydanticUndefined
            param_default = inspect.Parameter.empty if is_req else default
            raw_params.append((p.name, ann, param_default, is_req))

    return param_names, raw_params


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
        """Initialize RouteScanner with filtering and dispatch options."""
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

    def _is_path_allowed(self, path: str) -> bool:
        """Check whether path passes inclusion and exclusion rules."""
        for exc in self.exclude_paths:
            if exc.endswith("*") and path.startswith(exc[:-1]):
                return False
            if path in (exc, exc.rstrip("/")):
                return False

        if not self.include_paths:
            return True

        for inc in self.include_paths:
            if inc.endswith("*") and path.startswith(inc[:-1]):
                return True
            if path == inc:
                return True
        return False

    def should_include_route(self, route: APIRoute) -> bool:
        """Determines whether an APIRoute should be converted into an MCP tool."""
        if not self._is_path_allowed(route.path):
            return False

        methods = {m.upper() for m in route.methods} & self.include_methods
        if not methods:
            return False

        route_tags = set(route.tags or [])
        if self.exclude_tags and (route_tags & self.exclude_tags):
            return False
        if self.include_tags is not None and not bool(route_tags & self.include_tags):
            return False

        return True

    def _resolve_tool_meta(
        self,
        route: APIRoute,
        method: str,
        path_template: str,
    ) -> Tuple[str, str]:
        """Build sanitized tool name and documentation from route metadata."""
        endpoint = route.endpoint
        raw_name = getattr(endpoint, "mcp_tool_name", None) or getattr(
            endpoint, "_mcp_tool_name", None
        ) or route.operation_id or route.name

        if not raw_name or raw_name == "<lambda>":
            raw_name = f"{method.lower()}_{path_template}"
        tool_name = sanitize_tool_name(f"{self.tool_name_prefix}{raw_name}")

        endpoint_desc = getattr(endpoint, "mcp_tool_description", None) or getattr(
            endpoint, "_mcp_tool_description", None
        )
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

        return tool_name, tool_doc

    def convert_route(self, route: APIRoute) -> Tuple[str, str, Callable]:
        """Converts an APIRoute into an MCP tool callable with signature and docstring."""
        methods = [m.upper() for m in route.methods if m.upper() in self.include_methods]
        method = methods[0] if methods else "GET"
        path_template = route.path
        dep = route.dependant

        annotations: Dict[str, Any] = {}
        path_names, path_params = _collect_dependant_params(
            dep.path_params, annotations, is_path_param=True
        )
        query_names, query_params = _collect_dependant_params(
            dep.query_params, annotations, is_path_param=False
        )
        body_names, body_params = _collect_dependant_params(
            dep.body_params, annotations, is_path_param=False
        )

        all_params = path_params + query_params + body_params

        # Optional Dry-Run simulation parameter for state-modifying actions
        is_mutation = method in {"POST", "PUT", "DELETE", "PATCH"}
        if self.enable_dry_run and is_mutation:
            dry_desc = "[Dry Run] Validates input and simulates action without writing changes"
            dry_ann = Annotated[bool, Field(description=dry_desc)]
            annotations["dry_run"] = dry_ann
            all_params.append(("dry_run", dry_ann, False, False))

        sorted_params = sorted(all_params, key=lambda x: not x[3])
        parameters = [
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=ann,
                default=default,
            )
            for name, ann, default, _ in sorted_params
        ]

        annotations["return"] = Any
        sig = inspect.Signature(parameters=parameters, return_annotation=Any)
        tool_name, tool_doc = self._resolve_tool_meta(route, method, path_template)

        dispatcher = ASGIDispatcher(
            app=self.app,
            method=method,
            path_template=path_template,
            path_param_names=path_names,
            query_param_names=query_names,
            body_param_names=body_names,
            is_single_body_param=len(dep.body_params) == 1,
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
        setattr(tool_runner, "_mcp_tags", list(route.tags or []))
        setattr(tool_runner, "_mcp_path", path_template)
        setattr(tool_runner, "_mcp_method", method)

        return tool_name, tool_doc, tool_runner

    def scan(self) -> List[Tuple[str, str, Callable]]:
        """Scans all routes on the FastAPI application and returns converted tool tuples."""
        tools = []
        registered_names: Set[str] = set()

        for route in self.app.routes:
            if isinstance(route, APIRoute) and self.should_include_route(route):
                name, doc, runner = self.convert_route(route)
                base_name = name
                counter = 1
                while name in registered_names:
                    name = f"{base_name}_{counter}"
                    counter += 1
                registered_names.add(name)
                tools.append((name, doc, runner))

        return tools
