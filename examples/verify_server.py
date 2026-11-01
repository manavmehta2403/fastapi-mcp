"""Comprehensive Verification Suite for Hybrid FastAPI + FastMCP.

Tests all HTTP Verbs (GET, POST, PUT, PATCH, DELETE), Query and Path Parameters,
Server-Sent Events (SSE) streaming, Chunked token streaming, MCP Tool Calls,
and Native FastMCP transports.
"""

import json
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

BASE_URL = "http://127.0.0.1:8000"


def send_http_request(
    name: str,
    path: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    stream: bool = False,
) -> Tuple[bool, Optional[Any]]:
    """Send an HTTP request and report the test outcome."""
    url = f"{BASE_URL}{path}"
    print("\n=======================================================")
    print(f"Testing: {name}")
    print(f"{method} {url}")

    req_headers = {"User-Agent": "FastAPIMCPFullVerifier/1.0"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        print(f"Payload: {json.dumps(data)}")

    req = urllib.request.Request(url, method=method, headers=req_headers)

    try:
        with urllib.request.urlopen(req, data=body, timeout=5) as resp:
            status = resp.status
            content_type = resp.headers.get("content-type", "")

            if stream:
                print(f"[OK] Status {status} ({content_type}) - Stream Started")
                chunks = []
                for _ in range(2):
                    line = resp.readline().decode("utf-8", errors="ignore")
                    if not line:
                        break
                    chunks.append(line.strip())
                print(f"Stream sample received ({len(chunks)} lines):")
                for c in chunks:
                    if c:
                        print(f"  > {c}")
                return True, chunks

            content = resp.read()
            try:
                parsed = json.loads(content.decode("utf-8"))
                print(f"[OK] Status {status} ({content_type}):\n{json.dumps(parsed, indent=2)}")
                return True, parsed
            except Exception:  # pylint: disable=broad-exception-caught
                print(f"[OK] Status {status} ({content_type}): {len(content)} bytes")
                preview = content[:150].decode("utf-8", errors="ignore").replace("\n", " ")
                print(f"Preview: {preview}...")
                return True, content
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"[FAIL] Error: {e}")
        return False, None


def main() -> None:
    """Execute all verification tests across all verbs and streaming endpoints."""
    results = []

    # 1. VERB: GET with Query Parameters
    ok, _ = send_http_request(
        "1. GET /api/items (with Query parameters)",
        "/api/items?category=hardware&limit=2",
        method="GET",
    )
    results.append(ok)

    # 2. VERB: GET with Path Parameter
    ok, _ = send_http_request(
        "2. GET /api/items/{item_id} (with Path parameter)",
        "/api/items/1",
        method="GET",
    )
    results.append(ok)

    # 3. VERB: POST with Request Body
    ok, created = send_http_request(
        "3. POST /api/items (Create with Body)",
        "/api/items",
        method="POST",
        data={
            "name": "Superconducting QPU",
            "category": "quantum",
            "price": 4999.00,
            "tags": ["quantum", "qpu"],
        },
    )
    results.append(ok)
    created_id = created.get("item", {}).get("id") if (created and isinstance(created, dict)) else 4

    # 4. VERB: PUT with Path and Full Body
    ok, _ = send_http_request(
        "4. PUT /api/items/{item_id} (Full Update)",
        "/api/items/2",
        method="PUT",
        data={
            "name": "Smart Edge Sensor v2",
            "category": "iot",
            "price": 105.00,
            "in_stock": True,
        },
    )
    results.append(ok)

    # 5. VERB: PATCH with Path and Partial Body
    ok, _ = send_http_request(
        "5. PATCH /api/items/{item_id} (Partial Update)",
        "/api/items/2",
        method="PATCH",
        data={"price": 99.99},
    )
    results.append(ok)

    # 6. VERB: DELETE with Path and Query Parameter (deletes the newly created item)
    ok, _ = send_http_request(
        f"6. DELETE /api/items/{{item_id}} (Path + Query Param - Deleting ID {created_id})",
        f"/api/items/{created_id}?hard_delete=true",
        method="DELETE",
    )
    results.append(ok)

    # 7. VERB: QUERY (RFC 10008: Safe, Idempotent read with Request Body)
    ok, _ = send_http_request(
        "7. QUERY /api/items/query (HTTP QUERY Method / RFC 10008)",
        "/api/items/query",
        method="QUERY",
        data={"category": "hardware", "max_price": 500.0, "tags": ["gpu"]},
    )
    results.append(ok)

    # 8. Dual Endpoint (REST + MCP)
    ok, _ = send_http_request(
        "8. Dual Endpoint: POST /api/translate",
        "/api/translate",
        method="POST",
        data={"text": "All API verbs verified", "target_language": "es"},
    )
    results.append(ok)

    # 9. Dual Endpoint (PATCH with Discount)
    ok, _ = send_http_request(
        "9. Dual Endpoint: PATCH /api/items/{item_id}/discount",
        "/api/items/1/discount?percentage=15",
        method="PATCH",
    )
    results.append(ok)

    # 10. Server-Sent Events (SSE) Stream
    ok, _ = send_http_request(
        "10. Server-Sent Events (SSE) Stream: GET /api/events/sse",
        "/api/events/sse?events=3",
        method="GET",
        headers={"Accept": "text/event-stream"},
        stream=True,
    )
    results.append(ok)

    # 11. Chunked Token Streamable
    ok, _ = send_http_request(
        "11. Chunked Streamable: GET /api/stream/tokens",
        "/api/stream/tokens?prompt=Verifying+Chunked+Stream",
        method="GET",
        stream=True,
    )
    results.append(ok)

    # 12. Official MCP Swagger UI
    ok, _ = send_http_request(
        "12. Official MCP Swagger Docs UI: GET /mcp/docs",
        "/mcp/docs",
        method="GET",
    )
    results.append(ok)

    # 13. Dynamic MCP OpenAPI Specification
    ok, _ = send_http_request(
        "13. Dynamic MCP OpenAPI Spec: GET /mcp/openapi.json",
        "/mcp/openapi.json",
        method="GET",
    )
    results.append(ok)

    # 14. Offline Standalone Explorer
    ok, _ = send_http_request(
        "14. Offline Standalone Explorer: GET /mcp/ui",
        "/mcp/ui",
        method="GET",
    )
    results.append(ok)

    # 15. Direct Tool Execution (Swagger UI Endpoint)
    ok, _ = send_http_request(
        "15. Direct Tool Execution: POST /mcp/tools/search_internal_knowledge",
        "/mcp/tools/search_internal_knowledge",
        method="POST",
        data={"query": "production stability", "top_k": 2},
    )
    results.append(ok)

    # 16. FastMCP Tool Execution via UI Bridge
    ok, _ = send_http_request(
        "16. FastMCP Tool Execution via UI Bridge: /mcp/ui/call",
        "/mcp/ui/call",
        method="POST",
        data={
            "name": "search_internal_knowledge",
            "arguments": {"query": "production stability", "top_k": 2},
        },
    )
    results.append(ok)

    # 17. FastMCP Native SSE Transport Endpoint
    ok, _ = send_http_request(
        "17. FastMCP Native SSE Transport: GET /sse/",
        "/sse/",
        method="GET",
        headers={"Accept": "text/event-stream"},
        stream=True,
    )
    results.append(ok)

    passed_count = sum(results)
    total_count = len(results)
    print("\n" + "=" * 65)
    print(f"VERIFICATION SUMMARY: {passed_count}/{total_count} CHECKS PASSED")
    print("=" * 65 + "\n")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
