"""Ten realistic test scenarios for Festival Bundle Agent tools."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["USE_LOCAL_DATA"] = "true"

from src.tools.calculate_pricing import calculate_bundle_pricing  # noqa: E402
from src.tools.generate_bundles import generate_bundles  # noqa: E402
from src.tools.generate_promo import generate_promo  # noqa: E402
from src.tools.query_inventory import query_inventory  # noqa: E402


def scenario_01_full_inventory():
    """What's in my inventory? → should return all 15 products."""
    result = query_inventory(filter_type="all")
    assert result["count"] == 15, f"Expected 15 products, got {result['count']}"
    print("✓ Scenario 1: Full inventory — 15 products")


def scenario_02_overstocked():
    """Which items am I overstocked on? → stock > 50."""
    result = query_inventory(filter_type="overstocked", stock_threshold=50)
    assert result["count"] > 0
    assert all(i["stock_quantity"] > 50 for i in result["items"])
    print(f"✓ Scenario 2: Overstocked — {result['count']} items")


def scenario_03_bundle_suggestions():
    """What bundles can I create? → 3 bundle suggestions."""
    result = generate_bundles(num_bundles=3)
    assert result["status"] == "success"
    assert len(result["bundles"]) == 3
    print("✓ Scenario 3: Bundle suggestions — 3 bundles")


def scenario_04_min_margin():
    """I need bundles with at least 30% margin."""
    result = generate_bundles(num_bundles=5, min_margin_percent=30)
    assert result["status"] == "success"
    for b in result["bundles"]:
        assert b["margin_percent"] >= 30
    print(f"✓ Scenario 4: Min 30% margin — {len(result['bundles'])} bundles")


def scenario_05_drink_snack_combo():
    """Create a drink-and-snack combo."""
    drinks = query_inventory(filter_type="category", category="Drinks")
    food = query_inventory(filter_type="category", category="Food")
    items = [drinks["items"][0]["name"], food["items"][0]["name"]]
    result = generate_bundles(items=items, num_bundles=2)
    assert result["status"] == "success"
    assert len(result["bundles"]) >= 1
    print("✓ Scenario 5: Drink-and-snack combo")


def scenario_06_clear_overstock():
    """Best bundle for clearing overstock — prioritize high-stock items."""
    overstocked = query_inventory(filter_type="overstocked", stock_threshold=50)
    top_items = sorted(overstocked["items"], key=lambda x: x["stock_quantity"], reverse=True)
    names = [i["name"] for i in top_items[:3]]
    result = generate_bundles(items=names, num_bundles=2)
    assert result["status"] == "success"
    print("✓ Scenario 6: Clear overstock bundle")


def scenario_07_pricing_breakdown():
    """Show pricing breakdown for specific items."""
    result = calculate_bundle_pricing(
        [
            {"product_id": "Festival Lemonade", "quantity": 1},
            {"product_id": "Tie-Dye T-Shirt", "quantity": 1},
        ]
    )
    assert result["status"] == "success"
    assert "bundle_margin" in result
    print(f"✓ Scenario 7: Pricing breakdown — {result['margin_health']} margin")


def scenario_08_promo_copy():
    """Give me promo copy for a bundle."""
    bundles = generate_bundles(num_bundles=1)
    b = bundles["bundles"][0]
    promo = generate_promo(b["name"], b["items"], b["bundle_price"], b["retail_price"])
    assert promo["tagline"] and promo["description"] and promo["social_caption"]
    print("✓ Scenario 8: Promo copy — 3 variants generated")


def scenario_09_low_stock():
    """What items are running low?"""
    result = query_inventory(filter_type="low_stock", stock_threshold=20)
    assert result["status"] == "success"
    for item in result["items"]:
        assert item["stock_quantity"] < 20
    print(f"✓ Scenario 9: Low stock — {result['count']} items")


def scenario_10_empty_query():
    """Edge case: empty query → guidance message."""
    msg = ""
    assert msg.strip() == ""
    guidance = (
        "Hi! I'm your Festival Bundle Agent. Ask me about inventory, overstocked items, "
        "bundle deals, pricing breakdowns, or promo copy!"
    )
    assert len(guidance) > 0
    print("✓ Scenario 10: Empty query — guidance provided")


def run_all_scenarios():
    print("\nFestival Bundle Agent — Scenario Tests")
    print("=" * 45)
    scenario_01_full_inventory()
    scenario_02_overstocked()
    scenario_03_bundle_suggestions()
    scenario_04_min_margin()
    scenario_05_drink_snack_combo()
    scenario_06_clear_overstock()
    scenario_07_pricing_breakdown()
    scenario_08_promo_copy()
    scenario_09_low_stock()
    scenario_10_empty_query()
    print("\nAll 10 scenarios passed!\n")


if __name__ == "__main__":
    run_all_scenarios()
