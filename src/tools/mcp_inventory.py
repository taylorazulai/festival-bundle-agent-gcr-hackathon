"""Inventory queries via the official MongoDB MCP Server."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.mcp_client import MCPClient

logger = logging.getLogger(__name__)


async def mcp_query_inventory(
    mcp_client: MCPClient,
    filter_type: str = "all",
    category: str | None = None,
) -> dict[str, Any]:
    """
    Query inventory using the MongoDB MCP Server.
    Falls back gracefully if MCP is unavailable.
    """
    if not mcp_client or not mcp_client._initialized:
        return {"error": "MCP client not available", "products": []}

    try:
        query_filter: dict[str, Any] = {}
        if category:
            query_filter["category"] = category
        if filter_type == "overstocked":
            query_filter["stock_quantity"] = {"$gt": 50}
        elif filter_type == "low_stock":
            query_filter["stock_quantity"] = {"$lt": 20, "$gt": 0}

        db_name = os.getenv("MONGO_DB_NAME", "festival_bundle_agent")
        result = await mcp_client.call_tool(
            "find",
            {
                "database": db_name,
                "collection": "products",
                "filter": query_filter,
                "limit": 100,
            },
        )

        content = result.get("content", [])
        products: list[dict[str, Any]] = []
        for item in content:
            if item.get("type") == "text":
                try:
                    data = json.loads(item.get("text", "[]"))
                    if isinstance(data, list):
                        products.extend(data)
                    elif isinstance(data, dict):
                        products.append(data)
                except json.JSONDecodeError:
                    pass

        return {
            "source": "mongodb_mcp_server",
            "count": len(products),
            "products": products,
        }

    except Exception as exc:
        logger.error("MCP inventory query failed: %s", exc)
        return {"error": str(exc), "products": []}
