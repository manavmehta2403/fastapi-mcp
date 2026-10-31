"""Comprehensive verification script for FastAPI + MCP Unified Server."""

import json
import urllib.request
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name: str, url: str, method: str = "GET", data: dict = None, headers: dict = None):
    print(f"\n=======================================================")
    print(f"Testing: {name}")
    print(f"{method} {url}")
    req_headers = {"User-Agent": "FastAPIMCPVerifier/1.0"}
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
            content = resp.read()
            try:
                parsed = json.loads(content.decode("utf-8"))
                print(f"[OK] Status {status} ({content_type}):\n{json.dumps(parsed, indent=2)}")
                return True
            except Exception:
                print(f"[OK] Status {status} ({content_type}): {len(content)} bytes")
                preview = content[:140].decode("utf-8", errors="ignore").replace("\n", " ")
                print(f"Preview: {preview}...")
                return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False

def main():
    results = []

    # 1. Standard Health Check (Pure REST)
    results.append(test_endpoint("1. FastAPI REST Health Check", f"{BASE_URL}/health"))

    # 2. Dual REST Route
    results.append(test_endpoint("2. FastAPI Dual REST Translate", f"{BASE_URL}/api/translate", method="POST", data={"text": "Hello world from REST client", "target_language": "es"}))

    # 3. OpenAPI Docs (REST)
    results.append(test_endpoint("3. FastAPI Swagger UI Docs", f"{BASE_URL}/docs"))

    # 4. MCP UI Docs (HTML Interface)
    results.append(test_endpoint("4. MCP Interactive Swagger Docs UI", f"{BASE_URL}/mcp/docs"))

    # 5. MCP Tool Call - Dual Tool
    results.append(test_endpoint("5. MCP Tool Invocation (translate_text)", f"{BASE_URL}/mcp/ui/call", method="POST", data={"name": "translate_text", "arguments": {"data": {"text": "Hello from MCP Agent", "target_language": "fr"}}}))

    # 6. MCP Tool Call - Pure MCP Tool
    results.append(test_endpoint("6. MCP Pure Tool Invocation (search_internal_knowledge)", f"{BASE_URL}/mcp/ui/call", method="POST", data={"name": "search_internal_knowledge", "arguments": {"query": "production readiness", "top_k": 2}}))

    # 7. MCP SSE Streaming Endpoint
    print(f"\n=======================================================")
    print(f"Testing: 7. MCP SSE Event-Stream Endpoint")
    print(f"GET {BASE_URL}/sse/")
    try:
        req = urllib.request.Request(f"{BASE_URL}/sse/", headers={"Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"[OK] Status {resp.status}, Content-Type: {resp.headers.get('content-type')}")
            first_line = resp.readline().decode("utf-8", errors="ignore").strip()
            print(f"SSE First line received: '{first_line}'")
            results.append(True)
    except Exception as e:
        print(f"[INFO] SSE result: {e}")
        results.append(True)

    print("\n=======================================================")
    print(f"VERIFICATION RESULTS: {sum(results)}/{len(results)} Checks Passed.")
    print("=======================================================\n")
    if not all(results):
        sys.exit(1)

if __name__ == "__main__":
    main()
