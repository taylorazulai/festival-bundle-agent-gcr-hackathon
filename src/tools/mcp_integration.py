"""
MongoDB MCP (Model Context Protocol) Integration.

In production, connects to the official MongoDB MCP Server via src/mcp_client.py.
Falls back to direct pymongo when MCP is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.db.mongo_client import get_collection

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "mongodb-atlas-mcp"

_mcp_client: Any = None


def set_mcp_client(client: Any) -> None:
    """Register the connected MCP client (called during agent startup)."""
    global _mcp_client
    _mcp_client = client


def get_mcp_tools() -> list[dict[str, Any]]:
    """
    Returns tool definitions in MCP format for MongoDB Atlas operations.
    These would be exposed by the MCP server; here we implement the client-side handlers.
    """
    return [
        {
            "name": "mcp_query_inventory",
            "description": "Query inventory via MongoDB MCP Server",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "overstocked", "low_stock"],
                    },
                    "category": {"type": "string"},
                },
            },
        }
    ]


def _query_via_pymongo(
    filter_type: str = "all",
    category: str | None = None,
) -> dict[str, Any]:
    """Direct pymongo fallback when MCP server is unavailable."""
    coll = get_collection("products")
    if coll is None:
        return {
            "server": MCP_SERVER_NAME,
            "status": "error",
            "message": "MongoDB collection unavailable (local mode or not connected)",
            "count": 0,
            "products": [],
        }

    query: dict[str, Any] = {}
    if category:
        query["category"] = category
    if filter_type == "overstocked":
        query["stock_quantity"] = {"$gt": 50}
    elif filter_type == "low_stock":
        query["stock_quantity"] = {"$lt": 20, "$gt": 0}

    products = list(coll.find(query, {"_id": 0}))
    return {
        "server": MCP_SERVER_NAME,
        "status": "ok",
        "source": "pymongo_fallback",
        "count": len(products),
        "products": products,
    }


def mcp_query_inventory(
    filter_type: str = "all",
    category: str | None = None,
) -> dict[str, Any]:
    """Execute inventory query via MCP server, with pymongo fallback."""
    if _mcp_client is not None and getattr(_mcp_client, "_initialized", False):
        from src.tools.mcp_inventory import mcp_query_inventory as async_mcp_query

        try:
            result = asyncio.run(async_mcp_query(_mcp_client, filter_type, category))
            if result.get("error"):
                logger.warning("MCP query returned error, falling back to pymongo: %s", result["error"])
                return _query_via_pymongo(filter_type, category)
            return {
                "server": MCP_SERVER_NAME,
                "status": "ok",
                "source": result.get("source", "mongodb_mcp_server"),
                "count": result.get("count", 0),
                "products": result.get("products", []),
            }
        except Exception as exc:
            logger.warning("MCP query failed, falling back to pymongo: %s", exc)

    return _query_via_pymongo(filter_type, category)
