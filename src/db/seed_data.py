"""Seed MongoDB Atlas from JSON seed files with upsert logic."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from src.db.mongo_client import get_products_collection, get_sales_collection, is_local_mode  # noqa: E402


def _load_json(filename: str) -> list[dict]:
    path = PROJECT_ROOT / "data" / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_products() -> int:
    products = _load_json("seed_products.json")
    collection = get_products_collection()
    if collection is None:
        print(f"Local mode: {len(products)} products available from seed_products.json")
        return len(products)

    count = 0
    for product in products:
        collection.update_one({"name": product["name"]}, {"$set": product}, upsert=True)
        count += 1
    return count


def seed_sales() -> int:
    sales = _load_json("seed_sales.json")
    collection = get_sales_collection()
    if collection is None:
        print(f"Local mode: {len(sales)} sales records available from seed_sales.json")
        return len(sales)

    count = 0
    for sale in sales:
        key = {
            "product_id": sale["product_id"],
            "sale_date": sale["sale_date"],
            "event_name": sale["event_name"],
        }
        collection.update_one(key, {"$set": sale}, upsert=True)
        count += 1
    return count


def main() -> None:
    print("Festival Bundle Agent — Database Seeder")
    print("=" * 45)

    if is_local_mode():
        print("Note: USE_LOCAL_DATA=true or missing MONGO_URI — using local JSON files.")
        print("Set MONGO_URI in .env and USE_LOCAL_DATA=false to seed MongoDB Atlas.")

    product_count = seed_products()
    sales_count = seed_sales()

    print(f"Products seeded/available: {product_count}")
    print(f"Sales records seeded/available: {sales_count}")
    print("Done.")


if __name__ == "__main__":
    main()
