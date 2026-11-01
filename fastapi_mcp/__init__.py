"""FastAPI-MCP: Seamless bridge between FastAPI and FastMCP / Model Context Protocol.

Convert existing FastAPI applications to MCP servers with zero code changes,
or build unified APIs where REST endpoints and MCP tools coexist effortlessly.
"""

from .core import FastAPIMCP
from .scanner import RouteScanner
from .dispatcher import ASGIDispatcher

__version__ = "0.1.2"

__all__ = ["FastAPIMCP", "RouteScanner", "ASGIDispatcher"]
