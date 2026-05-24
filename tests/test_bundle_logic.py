"""Tests for bundle generation and pricing logic."""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["USE_LOCAL_DATA"] = "true"

from src.tools.calculate_pricing import calculate_bundle_pricing  # noqa: E402
from src.tools.generate_bundles import generate_bundles  # noqa: E402
from src.tools.generate_promo import generate_promo  # noqa: E402


@pytest.fixture(autouse=True)
def local_data():
    os.environ["USE_LOCAL_DATA"] = "true"


def test_generate_bundles_default():
    result = generate_bundles(num_bundles=3)
    assert result["status"] == "success"
    assert len(result["bundles"]) <= 3
    for bundle in result["bundles"]:
        assert 2 <= len(bundle["items"]) <= 4
        assert bundle["margin_percent"] >= 0
        assert bundle["bundle_price"] < bundle["retail_price"]


def test_generate_bundles_min_margin():
    result = generate_bundles(num_bundles=5, min_margin_percent=30)
    assert result["status"] == "success"
    for bundle in result["bundles"]:
        assert bundle["margin_percent"] >= 30


def test_generate_drink_food_bundle():
    result = generate_bundles(
        items=["Festival Lemonade", "Loaded Nachos"],
        num_bundles=2,
    )
    assert result["status"] == "success"
    assert len(result["bundles"]) >= 1


def test_calculate_pricing():
    result = calculate_bundle_pricing(
        [
            {"product_id": "Festival Lemonade", "quantity": 1},
            {"product_id": "Glow Stick Pack", "quantity": 1},
        ]
    )
    assert result["status"] == "success"
    assert result["total_retail"] > result["bundle_price"]
    assert result["margin_health"] in ("excellent", "good", "tight", "unprofitable")


def test_generate_promo():
    result = generate_promo(
        bundle_name="Summer Starter Pack",
        bundle_items=["Festival Lemonade", "Kettle Corn"],
        bundle_price=8.50,
        original_price=11.00,
    )
    assert result["status"] == "success"
    assert result["tagline"]
    assert result["description"]
    assert result["social_caption"]
    assert result["savings_amount"] == 2.5
