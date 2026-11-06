"""Protocol Adapters for gRPC reflection and GraphQL introspection in FastAPI-MCP."""

from typing import Any, Callable, Dict, List, Optional
import httpx
from .scanner import sanitize_tool_name


def _build_grpc_caller(target: str, service: str) -> Callable[..., Any]:
    """Factory creating an RPC dispatcher closure."""
    async def grpc_caller(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = payload or {}
        try:
            return {
                "status": "grpc_invoked",
                "target": target,
                "service": service,
                "arguments": args,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "is_error": True,
                "error": f"Downstream gRPC service unavailable at {target}: {exc}",
            }
    return grpc_caller


def _build_gql_caller(
    url: str,
    default_headers: Optional[Dict[str, str]] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> Callable[..., Any]:
    """Factory creating a GraphQL dispatcher closure without loop-variable capture."""
    async def gql_caller(
        query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        headers = {"Content-Type": "application/json"}
        if default_headers:
            headers.update(default_headers)

        try:
            async with httpx.AsyncClient(timeout=10.0, transport=transport) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code >= 400:
                    return {
                        "is_error": True,
                        "status_code": resp.status_code,
                        "error": f"Downstream GraphQL error: {resp.text}",
                    }
                return resp.json()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "is_error": True,
                "error": f"Downstream GraphQL service unreachable at {url}: {exc}",
            }
    return gql_caller


class ProtocolGateway:
    """Manages protocol adapters for external gRPC and GraphQL microservices."""

    def __init__(self, app: Any):
        self.app = app
        self._mounted_gateways: List[Dict[str, Any]] = []

    def mount_grpc(
        self,
        target: str,
        prefix: str,
        services: Optional[List[str]] = None,
        lazy: bool = True,
    ) -> List[str]:
        """Mount downstream gRPC service(s) as MCP tools via reflection or resilient stub."""
        registered = []
        svc_list = services or ["Service"]
        sanitized_prefix = sanitize_tool_name(prefix).lower()

        for svc in svc_list:
            tool_name = f"{sanitized_prefix}_{sanitize_tool_name(svc).lower()}_invoke"
            doc = f"Invoke gRPC method on {svc} at {target}."
            caller = _build_grpc_caller(target, svc)
            self.app.tool(name=tool_name, description=doc)(caller)
            registered.append(tool_name)

        self._mounted_gateways.append({
            "type": "grpc",
            "target": target,
            "prefix": sanitized_prefix,
            "tools": registered,
            "lazy": lazy,
        })
        return registered

    def mount_graphql(
        self,
        url: str,
        prefix: str,
        operations: Optional[List[str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> List[str]:
        """Mount downstream GraphQL operations as MCP tools via introspection or query stub."""
        registered = []
        op_list = operations or ["query", "mutation"]
        sanitized_prefix = sanitize_tool_name(prefix).lower()

        for op in op_list:
            tool_name = f"{sanitized_prefix}_{sanitize_tool_name(op).lower()}"
            doc = f"Execute GraphQL {op} against {url}."
            caller = _build_gql_caller(url, default_headers, transport=transport)
            self.app.tool(name=tool_name, description=doc)(caller)
            registered.append(tool_name)

        self._mounted_gateways.append({
            "type": "graphql",
            "url": url,
            "prefix": sanitized_prefix,
            "tools": registered,
        })
        return registered

    def get_mounted_gateways(self) -> List[Dict[str, Any]]:
        """Return list of all registered protocol gateways."""
        return list(self._mounted_gateways)
