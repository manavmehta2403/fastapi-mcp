"""Distributed Agent Mesh implementation for FastAPI-MCP."""

from typing import Any, Callable, Dict, List, Optional
import httpx
from .scanner import sanitize_tool_name


def _build_remote_proxy_caller(
    url: str,
    remote_tool_name: str,
    token: Optional[str] = None,
    max_hops: int = 5,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> Callable[..., Any]:
    """Factory creating a remote MCP proxy dispatcher with hop checks and tracing."""
    async def proxy_caller(
        payload: Optional[Dict[str, Any]] = None,
        mesh_hops: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if mesh_hops >= max_hops:
            return {
                "is_error": True,
                "error": f"Mesh hop limit exceeded ({max_hops}) - circular proxy loop detected.",
            }

        req_args = payload if payload is not None else kwargs
        headers = {
            "Content-Type": "application/json",
            "X-MCP-Mesh-Hops": str(mesh_hops + 1),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        target_url = f"{url.rstrip('/')}/tools/{remote_tool_name}"
        try:
            async with httpx.AsyncClient(timeout=15.0, transport=transport) as client:
                resp = await client.post(target_url, json=req_args, headers=headers)
                if resp.status_code >= 400:
                    return {
                        "is_error": True,
                        "status_code": resp.status_code,
                        "error": f"Downstream remote MCP error: {resp.text}",
                    }
                return resp.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return {
                "is_error": True,
                "error": f"Downstream remote MCP service unreachable at {url}: {exc}",
            }

    return proxy_caller


class AgentMesh:
    """Manages distributed MCP server proxying, routing, and cluster namespaces."""

    def __init__(self, app: Any, max_hops: int = 5):
        self.app = app
        self.max_hops = max_hops
        self._mounted_remotes: List[Dict[str, Any]] = []

    def mount_remote(
        self,
        url: str,
        prefix: str,
        tools: Optional[List[str]] = None,
        token: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> List[str]:
        """Mount and namespace a remote MCP server instance into the gateway catalog."""
        registered = []
        remote_tools = tools or ["query", "execute"]
        sanitized_prefix = sanitize_tool_name(prefix).lower()

        for t_name in remote_tools:
            clean_name = sanitize_tool_name(t_name).lower()
            proxied_name = f"{sanitized_prefix}_{clean_name}"
            doc = f"Proxied MCP tool '{t_name}' dispatched to {url}."

            caller = _build_remote_proxy_caller(
                url=url,
                remote_tool_name=clean_name,
                token=token,
                max_hops=self.max_hops,
                transport=transport,
            )
            self.app.tool(name=proxied_name, description=doc)(caller)
            registered.append(proxied_name)

        self._mounted_remotes.append({
            "url": url,
            "prefix": sanitized_prefix,
            "tools": registered,
            "token": "***" if token else None,
        })
        return registered

    def get_mounted_remotes(self) -> List[Dict[str, Any]]:
        """Return list of all mounted remote MCP servers."""
        return list(self._mounted_remotes)
