"""Tests for query_inventory tool."""

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["USE_LOCAL_DATA"] = "true"

from src.tools.query_inventory import query_inventory  # noqa: E402


@pytest.fixture(autouse=True)
def local_data():
    os.environ["USE_LOCAL_DATA"] = "true"


def test_query_all_inventory():
    result = query_inventory(filter_type="all")
    assert result["status"] == "success"
    assert result["count"] == 15
    assert all("inventory_value" in item for item in result["items"])


def test_query_overstocked():
    result = query_inventory(filter_type="overstocked", stock_threshold=50)
    assert result["status"] == "success"
    assert result["count"] > 0
    for item in result["items"]:
        assert item["stock_quantity"] > 50


def test_query_low_stock():
    result = query_inventory(filter_type="low_stock", stock_threshold=20)
    assert result["status"] == "success"
    for item in result["items"]:
        assert 0 < item["stock_quantity"] < 20


def test_query_by_category():
    result = query_inventory(filter_type="category", category="Drinks")
    assert result["status"] == "success"
    assert all(item["category"] == "Drinks" for item in result["items"])


def test_category_requires_name():
    result = query_inventory(filter_type="category")
    assert result["status"] == "error"
