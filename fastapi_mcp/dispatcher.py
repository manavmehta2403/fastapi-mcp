import json
import urllib.parse
from typing import Any, Callable, Dict, Optional, Set
import httpx
from fastapi import FastAPI


class ASGIDispatcher:
    """Dispatches in-memory requests to a FastAPI application using httpx ASGITransport."""

    def __init__(
        self,
        app: FastAPI,
        method: str,
        path_template: str,
        path_param_names: Set[str],
        query_param_names: Set[str],
        body_param_names: Set[str],
        is_single_body_param: bool = True,
        headers_factory: Optional[Callable[[], Dict[str, str]]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.app = app
        self.method = method.upper()
        self.path_template = path_template
        self.path_param_names = path_param_names
        self.query_param_names = query_param_names
        self.body_param_names = body_param_names
        self.is_single_body_param = is_single_body_param
        self.headers_factory = headers_factory
        self.default_headers = default_headers or {}

    def _serialize_val(self, val: Any) -> Any:
        if hasattr(val, "model_dump"):
            return val.model_dump(mode="json")
        if hasattr(val, "dict"):
            return val.dict()
        return val

    async def __call__(self, **kwargs: Any) -> Any:
        # 1. Format URL path
        url_path = self.path_template
        for pname in self.path_param_names:
            if pname in kwargs:
                raw_val = kwargs[pname]
                encoded_val = urllib.parse.quote(str(raw_val), safe="")
                url_path = url_path.replace(f"{{{pname}}}", encoded_val)

        # 2. Collect query params
        params: Dict[str, Any] = {}
        for qname in self.query_param_names:
            if qname in kwargs and kwargs[qname] is not None:
                params[qname] = self._serialize_val(kwargs[qname])

        # 3. Collect body params
        json_body = None
        if self.is_single_body_param and self.body_param_names:
            bname = next(iter(self.body_param_names))
            if bname in kwargs and kwargs[bname] is not None:
                json_body = self._serialize_val(kwargs[bname])
        elif self.body_param_names:
            json_body = {}
            for bname in self.body_param_names:
                if bname in kwargs and kwargs[bname] is not None:
                    json_body[bname] = self._serialize_val(kwargs[bname])

        # 4. Resolve headers
        headers = dict(self.default_headers)
        if self.headers_factory:
            dynamic_headers = self.headers_factory()
            if dynamic_headers:
                headers.update(dynamic_headers)

        # 5. Dispatch in-memory via ASGI transport
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://internal") as client:
            resp = await client.request(
                method=self.method,
                url=url_path,
                params=params if params else None,
                json=json_body if json_body is not None else None,
                headers=headers if headers else None,
            )

            try:
                data = resp.json()
            except Exception:
                data = resp.text

            if resp.status_code >= 400:
                return {
                    "is_error": True,
                    "status_code": resp.status_code,
                    "detail": data,
                }

            return data
