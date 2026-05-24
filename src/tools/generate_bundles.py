"""Bundle generation logic for festival inventory — bounded, deterministic."""

from __future__ import annotations

import time
from typing import Any

from src.agent_config import BUNDLE_NAMES
from src.db.mongo_client import find_all_products, find_products, is_local_mode
from src.utils.logging_config import get_logger

logger = get_logger("generate_bundles")

MAX_BUNDLE_TIME = 8.0
MAX_ATTEMPTS = 20


def generate_bundles(
    items: list[str] | None = None,
    max_bundle_size: int = 4,
    target_discount_percent: float = 15,
    num_bundles: int = 3,
    min_margin_percent: float | None = None,
) -> dict[str, Any]:
    """Generate product bundle recommendations — always terminates within 8 seconds."""
    start = time.time()
    try:
        max_bundle_size = max(2, min(4, int(max_bundle_size)))
        num_bundles = max(1, int(num_bundles))

        all_products = find_all_products()

        if items:
            if items and isinstance(items[0], str):
                name_map = {p["name"]: p for p in all_products}
                candidates = [name_map[n] for n in items if n in name_map]
            else:
                candidates = find_products({"name": {"$in": items}})
            if not candidates:
                candidates = all_products[:10]
        else:
            candidates = [p for p in all_products if p.get("stock_quantity", 0) > 50]
            if not candidates:
                candidates = all_products[:10]

        categories: dict[str, list[dict[str, Any]]] = {}
        for p in candidates:
            cat = p.get("category", "General")
            categories.setdefault(cat, []).append(p)

        cat_names = list(categories.keys())
        bundles: list[dict[str, Any]] = []
        attempts = 0

        while len(bundles) < num_bundles and attempts < MAX_ATTEMPTS:
            attempts += 1
            if time.time() - start > MAX_BUNDLE_TIME:
                logger.warning("generate_bundles hit MAX_BUNDLE_TIME guard")
                break

            bundle_items: list[dict[str, Any]] = []
            if len(cat_names) >= 2:
                primary = categories[cat_names[attempts % len(cat_names)]]
                secondary = categories[cat_names[(attempts + 1) % len(cat_names)]]
                p1 = primary[attempts % len(primary)]
                p2 = secondary[(attempts + 1) % len(secondary)]
                bundle_items = [p1, p2]
                if len(cat_names) >= 3 and attempts % 2 == 0:
                    tertiary = categories[cat_names[(attempts + 2) % len(cat_names)]]
                    p3 = tertiary[attempts % len(tertiary)]
                    bundle_items.append(p3)
            else:
                bundle_items = candidates[: min(max_bundle_size, 3)]

            if not bundle_items:
                continue

            total_retail = sum(float(p["sell_price"]) for p in bundle_items)
            total_cost = sum(
                float(p.get("unit_cost", float(p["sell_price"]) * 0.6)) for p in bundle_items
            )
            bundle_price = round(total_retail * (1 - target_discount_percent / 100), 2)
            margin = (
                round(((bundle_price - total_cost) / bundle_price) * 100, 1)
                if bundle_price > 0
                else 0.0
            )

            if min_margin_percent is not None and margin < min_margin_percent:
                continue

            name = BUNDLE_NAMES[len(bundles) % len(BUNDLE_NAMES)]
            bundles.append(
                {
                    "name": name,
                    "items": [p["name"] for p in bundle_items],
                    "retail_price": round(total_retail, 2),
                    "bundle_price": bundle_price,
                    "discount_percent": target_discount_percent,
                    "cost": round(total_cost, 2),
                    "margin_percent": margin,
                }
            )

        logger.info(
            "Generated bundles",
            extra={
                "extra_data": {
                    "count": len(bundles),
                    "elapsed_s": round(time.time() - start, 3),
                    "local_mode": is_local_mode(),
                }
            },
        )
        return {"status": "success", "bundles": bundles, "count": len(bundles)}

    except Exception as exc:
        logger.error("generate_bundles failed", extra={"extra_data": {"error": str(exc)}})
        return {
            "status": "error",
            "error": str(exc),
            "bundles": [
                {
                    "name": "Quick Bundle (Error Fallback)",
                    "items": ["Festival Lemonade", "Kettle Corn"],
                    "retail_price": 10.0,
                    "bundle_price": 8.50,
                    "discount_percent": 15,
                    "cost": 5.0,
                    "margin_percent": 41.2,
                }
            ],
            "count": 1,
        }


def generate_bundles_tool(
    items: list[str] | None = None,
    max_bundle_size: int = 4,
    target_discount_percent: float = 15,
    num_bundles: int = 3,
    min_margin_percent: float | None = None,
) -> dict[str, Any]:
    """ADK-compatible wrapper for generate_bundles."""
    return generate_bundles(
        items=items or None,
        max_bundle_size=max_bundle_size,
        target_discount_percent=target_discount_percent,
        num_bundles=num_bundles,
        min_margin_percent=min_margin_percent,
    )
