"""Rule-based chat fallback when ADK/Gemini is unavailable."""

from __future__ import annotations

from typing import Any

MAX_FALLBACK_TOOL_CALLS = 2


async def process_message_fallback(message: str) -> dict[str, Any]:
    """Keyword-driven tool routing — same behavior as local rule-based mode."""
    from src.tools.calculate_pricing import calculate_bundle_pricing
    from src.tools.generate_bundles import generate_bundles
    from src.tools.generate_promo import generate_promo
    from src.tools.query_inventory import query_inventory

    msg = message.lower().strip()
    tool_calls: list[dict[str, Any]] = []

    def _record(name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        tool_calls.append({"name": name, "args": args, "result": result})
        return result

    def _can_call() -> bool:
        return len(tool_calls) < MAX_FALLBACK_TOOL_CALLS

    def _format_bundles(bundles_payload: dict[str, Any]) -> str:
        bundle_list = bundles_payload.get("bundles", [])
        if not bundle_list:
            return "I couldn't generate bundles with the current inventory."
        lines = [f"**{len(bundle_list)} Bundle Recommendations:**\n"]
        for b in bundle_list:
            savings = b["retail_price"] - b["bundle_price"]
            lines.append(
                f"### {b['name']}\n"
                f"Items: {', '.join(b['items'])}\n"
                f"Retail: ${b['retail_price']:.2f} → Bundle: ${b['bundle_price']:.2f} "
                f"(Save ${savings:.2f}!)\n"
                f"Margin: {b['margin_percent']:.1f}%\n"
            )
        return "\n".join(lines)

    def _extract_bundles() -> list[dict[str, Any]]:
        bundles: list[dict[str, Any]] = []
        for tc in tool_calls:
            if tc.get("name") == "generate_bundles":
                result = tc.get("result") or {}
                bundles.extend(result.get("bundles", []))
        return bundles

    if not msg:
        return {
            "response": (
                "Hi! I'm your Festival Bundle Agent. Ask me about inventory, overstocked items, "
                "bundle deals, pricing breakdowns, or promo copy!"
            ),
            "tool_calls": [],
            "bundles": [],
            "timeout": False,
        }

    if "overstock" in msg:
        result = _record(
            "query_inventory",
            {"filter_type": "overstocked"},
            query_inventory(filter_type="overstocked", stock_threshold=50),
        )
        items = result.get("items", [])
        lines = [f"**Overstocked items ({len(items)}):**"]
        for item in items:
            lines.append(
                f"- {item['name']} ({item['category']}): {item['stock_quantity']} units, "
                f"${item['inventory_value']:.2f} inventory value"
            )
        return {"response": "\n".join(lines), "tool_calls": tool_calls, "bundles": [], "timeout": False}

    if "low" in msg and "stock" in msg:
        result = _record(
            "query_inventory",
            {"filter_type": "low_stock"},
            query_inventory(filter_type="low_stock", stock_threshold=20),
        )
        items = result.get("items", [])
        lines = [f"**Low stock items ({len(items)}):**"]
        for item in items:
            lines.append(f"- {item['name']}: {item['stock_quantity']} units left")
        return {"response": "\n".join(lines), "tool_calls": tool_calls, "bundles": [], "timeout": False}

    if "inventory" in msg or "what's in" in msg:
        result = _record(
            "query_inventory",
            {"filter_type": "all"},
            query_inventory(filter_type="all"),
        )
        items = result.get("items", [])
        return {
            "response": (
                f"**Full inventory: {len(items)} products.** "
                "Use overstock or bundle queries for recommendations."
            ),
            "tool_calls": tool_calls,
            "bundles": [],
            "timeout": False,
        }

    if ("promo" in msg or "copy" in msg) and _can_call():
        bundle_args = {"num_bundles": 1}
        bundles = _record("generate_bundles", bundle_args, generate_bundles(**bundle_args))
        if bundles.get("bundles") and _can_call():
            b = bundles["bundles"][0]
            promo_args = {
                "bundle_name": b["name"],
                "bundle_items": b["items"],
                "bundle_price": b["bundle_price"],
                "original_price": b["retail_price"],
            }
            promo = _record("generate_promo", promo_args, generate_promo(**promo_args))
            return {
                "response": (
                    f"**{b['name']} Promo Copy:**\n\n"
                    f"Tagline: {promo['tagline']}\n\n"
                    f"Description: {promo['description']}\n\n"
                    f"Social: {promo['social_caption']}"
                ),
                "tool_calls": tool_calls,
                "bundles": _extract_bundles(),
                "timeout": False,
            }

    if ("bundle" in msg or "combo" in msg or "deal" in msg or "create" in msg) and _can_call():
        bundle_args: dict[str, Any] = {"num_bundles": 3}
        if "margin" in msg and "30" in msg:
            bundle_args = {"num_bundles": 5, "min_margin_percent": 30}
        bundles = _record("generate_bundles", bundle_args, generate_bundles(**bundle_args))
        return {
            "response": _format_bundles(bundles),
            "tool_calls": tool_calls,
            "bundles": _extract_bundles(),
            "timeout": False,
        }

    if ("pricing" in msg or "breakdown" in msg) and _can_call():
        bundles = _record(
            "generate_bundles",
            {"num_bundles": 1},
            generate_bundles(num_bundles=1),
        )
        if bundles.get("bundles"):
            b = bundles["bundles"][0]
            return {
                "response": (
                    f"**Pricing for {b['name']}:**\n"
                    f"Retail: ${b['retail_price']:.2f} → Bundle: ${b['bundle_price']:.2f}\n"
                    f"Margin: {b['margin_percent']:.1f}%"
                ),
                "tool_calls": tool_calls,
                "bundles": _extract_bundles(),
                "timeout": False,
            }
        return {
            "response": "No bundles available for pricing.",
            "tool_calls": tool_calls,
            "bundles": [],
            "timeout": False,
        }

    if _can_call():
        bundles = _record(
            "generate_bundles",
            {"num_bundles": 3},
            generate_bundles(num_bundles=3),
        )
        return {
            "response": _format_bundles(bundles),
            "tool_calls": tool_calls,
            "bundles": _extract_bundles(),
            "timeout": False,
        }

    return {
        "response": (
            "I can help with inventory, bundles, pricing, and promo copy. "
            "Try: 'Show overstocked items' or 'What bundles can I create?'"
        ),
        "tool_calls": tool_calls,
        "bundles": [],
        "timeout": False,
    }
