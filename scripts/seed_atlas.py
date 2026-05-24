#!/usr/bin/env python3
"""Seed MongoDB Atlas from JSON files (production; ignores USE_LOCAL_DATA)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from pymongo import MongoClient, ReplaceOne

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")


def _load_json(filename: str) -> list[dict]:
    path = PROJECT_ROOT / "data" / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _cluster_name_from_uri(mongo_uri: str) -> str:
    host = urlparse(mongo_uri).hostname or "unknown"
    if host.endswith(".mongodb.net"):
        return host.split(".")[0]
    return host


def main() -> None:
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri or "<user>" in mongo_uri:
        print("ERROR: Set MONGO_URI in .env before running seed_atlas.py", file=sys.stderr)
        sys.exit(1)

    cluster_name = _cluster_name_from_uri(mongo_uri)
    db_name = os.getenv("MONGO_DB_NAME", "festival_bundle_agent")

    products = _load_json("seed_products.json")
    sales = _load_json("seed_sales.json")

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        maxPoolSize=10,
    )
    client.admin.command("ping")

    db = client[db_name]
    products_coll = db["products"]
    sales_coll = db["sales_history"]

    product_ops = [
        ReplaceOne({"name": p["name"]}, p, upsert=True) for p in products
    ]
    sales_ops = [
        ReplaceOne(
            {
                "product_id": s["product_id"],
                "sale_date": s["sale_date"],
                "event_name": s["event_name"],
            },
            s,
            upsert=True,
        )
        for s in sales
    ]

    if product_ops:
        products_coll.bulk_write(product_ops)
    if sales_ops:
        sales_coll.bulk_write(sales_ops)

    client.close()
    print(
        f"Seeded {len(products)} products and {len(sales)} sales records "
        f"to MongoDB Atlas cluster: {cluster_name}"
    )


if __name__ == "__main__":
    main()
