"""Command-line interface for running and inspecting FastAPI-MCP apps."""

import argparse
import asyncio
import importlib
import json
import sys
from typing import Any
from fastapi import FastAPI

from .core import FastAPIMCP


def load_app(app_str: str) -> Any:
    """Loads an application instance from a 'module:attribute' string."""
    if ":" not in app_str:
        raise ValueError(f"Invalid app string format '{app_str}'. Expected 'module:attribute' (e.g., 'main:app')")

    module_name, attr_name = app_str.split(":", 1)
    is_factory = False
    if attr_name.endswith("()"):
        attr_name = attr_name[:-2]
        is_factory = True
    
    # Ensure current working directory is in sys.path
    if "." not in sys.path:
        sys.path.insert(0, ".")

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"Could not import module '{module_name}': {e}") from e

    if not hasattr(module, attr_name):
        raise AttributeError(f"Module '{module_name}' has no attribute '{attr_name}'")

    app = getattr(module, attr_name)
    if is_factory or (callable(app) and not isinstance(app, FastAPI)):
        app = app()
    return app


def main() -> None:
    """Run the FastAPI-MCP command-line interface."""
    parser = argparse.ArgumentParser(
        prog="fastapi-mcp",
        description="FastAPI-MCP: Run or inspect FastAPI applications as MCP servers",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run application as an MCP server")
    run_parser.add_argument("app", help="Application target, e.g. 'main:app'")
    run_parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    run_parser.add_argument("--name", help="Custom MCP server name", default="FastAPIMCP")

    # inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect and list tools generated from the application")
    inspect_parser.add_argument("app", help="Application target, e.g. 'main:app'")
    inspect_parser.add_argument("--json", action="store_true", help="Output full tool definitions as JSON")

    args = parser.parse_args()

    app = load_app(args.app)

    if isinstance(app, FastAPIMCP):
        mcp = app
    elif isinstance(app, FastAPI):
        mcp = FastAPIMCP.bind(app, name=getattr(args, "name", "FastAPIMCP"), mount_path=None, mount_sse_path=None)
    else:
        raise TypeError(f"Target object must be a FastAPI or FastAPIMCP instance, got {type(app)}")

    if args.command == "inspect":
        async def do_inspect():
            tools = await mcp.list_tools()
            if args.json:
                data = [t.model_dump() for t in tools]
                print(json.dumps(data, indent=2))
            else:
                print(f"=== FastAPI-MCP Server: {mcp.mcp_name} ===")
                print(f"Found {len(tools)} tools:")
                for t in tools:
                    print(f"\n* Tool: {t.name}")
                    print(f"  Description: {t.description}")
                    props = t.input_schema.get("properties", {})
                    reqs = t.input_schema.get("required", [])
                    print(f"  Arguments ({len(props)}):")
                    for p_name, p_info in props.items():
                        req_str = " (required)" if p_name in reqs else f" (default: {p_info.get('default')})"
                        desc_str = f" - {p_info.get('description')}" if p_info.get("description") else ""
                        print(f"    - {p_name}: {p_info.get('type')}{req_str}{desc_str}")

        asyncio.run(do_inspect())

    elif args.command == "run":
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
