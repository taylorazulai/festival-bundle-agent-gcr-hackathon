"""Margin and pricing calculations for bundles."""

from __future__ import annotations

from typing import Any

from src.db.mongo_client import find_product_by_name
from src.utils.logging_config import get_logger

logger = get_logger("calculate_pricing")


def _margin_health(margin_percent: float) -> str:
    if margin_percent > 50:
        return "excellent"
    if margin_percent >= 30:
        return "good"
    if margin_percent >= 15:
        return "tight"
    return "unprofitable"


def calculate_bundle_pricing(
    bundle_items: list[dict[str, Any]],
    discount_percent: float = 15,
) -> dict[str, Any]:
    """Calculate detailed pricing and margin analysis for a product bundle.

    Breaks down costs, retail prices, and margin impact for each item and the total bundle.

    Args:
        bundle_items: List of objects with product_id (name) and quantity (default 1).
        discount_percent: Discount to apply to combined retail price.

    Returns:
        Detailed pricing breakdown with per-item and total calculations.
    """
    try:
        if not bundle_items:
            return {"status": "error", "message": "bundle_items cannot be empty"}

        item_breakdown: list[dict[str, Any]] = []
        total_cost = 0.0
        total_retail = 0.0

        for entry in bundle_items:
            product_id = entry.get("product_id") or entry.get("name")
            quantity = int(entry.get("quantity", 1))
            if not product_id:
                return {"status": "error", "message": "Each bundle item requires product_id"}

            product = find_product_by_name(str(product_id))
            if not product:
                return {
                    "status": "error",
                    "message": f"Product not found: {product_id}",
                }

            unit_cost = float(product["unit_cost"])
            sell_price = float(product["sell_price"])
            individual_cost = round(unit_cost * quantity, 2)
            individual_retail = round(sell_price * quantity, 2)
            individual_margin = (
                round(((sell_price - unit_cost) / sell_price) * 100, 2) if sell_price else 0.0
            )

            total_cost += individual_cost
            total_retail += individual_retail

            item_breakdown.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "sell_price": sell_price,
                    "individual_cost": individual_cost,
                    "individual_retail": individual_retail,
                    "individual_margin": individual_margin,
                }
            )

        bundle_price = round(total_retail * (1 - discount_percent / 100), 2)
        bundle_margin = (
            round(((bundle_price - total_cost) / bundle_price) * 100, 2) if bundle_price else 0.0
        )

        result = {
            "status": "success",
            "items": item_breakdown,
            "total_cost": round(total_cost, 2),
            "total_retail": round(total_retail, 2),
            "discount_percent": discount_percent,
            "bundle_price": bundle_price,
            "bundle_margin": bundle_margin,
            "margin_health": _margin_health(bundle_margin),
        }

        logger.info(
            "Calculated bundle pricing",
            extra={"extra_data": {"items": len(item_breakdown), "margin": bundle_margin}},
        )
        return result

    except Exception as exc:
        logger.error("calculate_bundle_pricing failed", extra={"extra_data": {"error": str(exc)}})
        return {"status": "error", "message": str(exc)}


def calculate_pricing_tool(
    bundle_items: list[dict[str, Any]],
    discount_percent: float = 15,
) -> dict[str, Any]:
    """ADK-compatible wrapper for calculate_bundle_pricing."""
    return calculate_bundle_pricing(bundle_items=bundle_items, discount_percent=discount_percent)
