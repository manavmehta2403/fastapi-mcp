"""In-memory ASGI dispatcher for FastAPI-MCP tools.

Dispatches MCP tool invocations to FastAPI applications via httpx.ASGITransport,
preserving dependency injection, validation, and middleware without network overhead.
"""

import inspect
from typing import Any, Callable, Dict, Optional, Set
import urllib.parse
from fastapi import FastAPI
import httpx


def _serialize_val(val: Any) -> Any:
    """Serialize Pydantic models or dictionaries to JSON-compatible data."""
    if hasattr(val, "model_dump"):
        return val.model_dump(mode="json")
    if hasattr(val, "dict"):
        return val.dict()
    return val


class ASGIDispatcher:
    """Dispatches in-memory requests to a FastAPI application using httpx ASGITransport."""

    def __init__(
        self,
        app: FastAPI,
        method: str,
        path_template: str,
        *,
        path_param_names: Set[str],
        query_param_names: Set[str],
        body_param_names: Set[str],
        is_single_body_param: bool = True,
        headers_factory: Optional[Callable[[], Dict[str, str]]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        session_context_provider: Optional[Callable[[Dict[str, Any]], Dict[str, str]]] = None,
        enable_dry_run: bool = False,
    ):
        """Initialize ASGIDispatcher with route metadata and execution context."""
        self.app = app
        self.method = method.upper()
        self.path_template = path_template
        self.path_param_names = path_param_names
        self.query_param_names = query_param_names
        self.body_param_names = body_param_names
        self.is_single_body_param = is_single_body_param
        self.headers_factory = headers_factory
        self.default_headers = default_headers or {}
        self.session_context_provider = session_context_provider
        self.enable_dry_run = enable_dry_run

    def _build_url_path(self, kwargs: Dict[str, Any]) -> str:
        """Substitute URL path parameters with safely encoded values."""
        url_path = self.path_template
        for pname in self.path_param_names:
            if pname in kwargs:
                raw_val = kwargs[pname]
                encoded_val = urllib.parse.quote(str(raw_val), safe="")
                url_path = url_path.replace(f"{{{pname}}}", encoded_val)
        return url_path

    def _build_query_params(self, kwargs: Dict[str, Any], is_dry_run: bool) -> Dict[str, Any]:
        """Collect and serialize query parameters."""
        params: Dict[str, Any] = {}
        for qname in self.query_param_names:
            if qname in kwargs and kwargs[qname] is not None:
                params[qname] = _serialize_val(kwargs[qname])
        if is_dry_run:
            params["dry_run"] = "true"
        return params

    def _build_body(self, kwargs: Dict[str, Any]) -> Optional[Any]:
        """Collect and serialize body parameters."""
        if self.is_single_body_param and self.body_param_names:
            bname = next(iter(self.body_param_names))
            if bname in kwargs and kwargs[bname] is not None:
                return _serialize_val(kwargs[bname])
            return None

        if self.body_param_names:
            json_body: Dict[str, Any] = {}
            for bname in self.body_param_names:
                if bname in kwargs and kwargs[bname] is not None:
                    json_body[bname] = _serialize_val(kwargs[bname])
            return json_body
        return None

    def _resolve_headers(self, kwargs: Dict[str, Any], is_dry_run: bool) -> Dict[str, str]:
        """Resolve static, factory, and dynamic session context headers."""
        headers = dict(self.default_headers)
        if self.headers_factory:
            dynamic_headers = self.headers_factory()
            if dynamic_headers:
                headers.update(dynamic_headers)

        provider = getattr(self.app, "_mcp_session_context_provider", None) or (
            self.session_context_provider
        )
        if provider:
            sig = inspect.signature(provider)
            session_headers = provider() if len(sig.parameters) == 0 else provider(kwargs)
            if session_headers:
                headers.update(session_headers)

        if is_dry_run:
            headers["X-Dry-Run"] = "true"
        return headers

    def _parse_response(self, resp: httpx.Response, is_dry_run: bool) -> Any:
        """Parse HTTP response into JSON or fallback text, adding dry-run wrapper if active."""
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = resp.json()
            except Exception:  # pylint: disable=broad-exception-caught
                data = resp.text
        else:
            data = resp.text

        if resp.status_code >= 400:
            return {
                "is_error": True,
                "status_code": resp.status_code,
                "detail": data,
            }

        if is_dry_run:
            return {
                "dry_run": True,
                "simulated": True,
                "result": data,
            }

        return data

    async def __call__(self, **kwargs: Any) -> Any:
        """Execute in-memory request to the FastAPI application and return result."""
        is_dry_run = bool(kwargs.pop("dry_run", False))
        url_path = self._build_url_path(kwargs)
        params = self._build_query_params(kwargs, is_dry_run)
        json_body = self._build_body(kwargs)
        headers = self._resolve_headers(kwargs, is_dry_run)

        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            resp = await client.request(
                method=self.method,
                url=url_path,
                params=params if params else None,
                json=json_body,
                headers=headers if headers else None,
            )
            return self._parse_response(resp, is_dry_run)
