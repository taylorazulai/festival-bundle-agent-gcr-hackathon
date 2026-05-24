"""MongoDB inventory query tool."""

from __future__ import annotations

from typing import Any, Literal

from src.db.mongo_client import find_products
from src.utils.logging_config import get_logger

logger = get_logger("query_inventory")

FilterType = Literal["all", "overstocked", "low_stock", "category"]


def _format_product(product: dict[str, Any]) -> dict[str, Any]:
    stock = int(product.get("stock_quantity", 0))
    sell_price = float(product.get("sell_price", 0))
    return {
        "name": product["name"],
        "category": product["category"],
        "unit_cost": float(product.get("unit_cost", 0)),
        "sell_price": sell_price,
        "stock_quantity": stock,
        "inventory_value": round(stock * sell_price, 2),
    }


def query_inventory(
    filter_type: FilterType = "all",
    category: str | None = None,
    stock_threshold: float = 50,
) -> dict[str, Any]:
    """Query festival product inventory from MongoDB Atlas.

    Returns product details including name, category, cost, sell price, and stock quantity.

    Args:
        filter_type: Type of inventory filter — all, overstocked, low_stock, or category.
        category: Filter by product category (required when filter_type is category).
        stock_threshold: Stock quantity threshold for overstocked/low_stock filters.

    Returns:
        Dictionary with status and list of inventory items.
    """
    try:
        threshold = int(stock_threshold)
        query: dict[str, Any] = {}

        if filter_type == "overstocked":
            query["stock_quantity"] = {"$gt": threshold}
        elif filter_type == "low_stock":
            products = find_products({})
            items = [
                _format_product(p)
                for p in products
                if 0 < int(p.get("stock_quantity", 0)) < threshold
            ]
            logger.info(
                "Queried low_stock inventory",
                extra={"extra_data": {"count": len(items), "threshold": threshold}},
            )
            return {"status": "success", "filter_type": filter_type, "items": items, "count": len(items)}
        elif filter_type == "category":
            if not category:
                return {
                    "status": "error",
                    "message": "category parameter is required when filter_type is 'category'",
                    "items": [],
                }
            query["category"] = category
        elif filter_type != "all":
            return {
                "status": "error",
                "message": f"Invalid filter_type: {filter_type}",
                "items": [],
            }

        products = find_products(query)
        items = [_format_product(p) for p in products]
        logger.info(
            "Queried inventory",
            extra={"extra_data": {"filter_type": filter_type, "count": len(items)}},
        )
        return {"status": "success", "filter_type": filter_type, "items": items, "count": len(items)}

    except Exception as exc:
        logger.error("query_inventory failed", extra={"extra_data": {"error": str(exc)}})
        return {"status": "error", "message": str(exc), "items": []}


def query_inventory_tool(
    filter_type: str = "all",
    category: str | None = None,
    stock_threshold: float = 50,
) -> dict[str, Any]:
    """ADK-compatible wrapper for query_inventory."""
    return query_inventory(
        filter_type=filter_type,  # type: ignore[arg-type]
        category=category,
        stock_threshold=stock_threshold,
    )
