"""MongoDB Atlas connection with pooling, singleton client, and local JSON fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.logging_config import get_logger

if TYPE_CHECKING:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database

logger = get_logger("mongo_client")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

_mongo_client: MongoClient | None = None
_db: Database | None = None
_use_local: bool = False
_local_products: list[dict[str, Any]] = []
_local_sales: list[dict[str, Any]] = []

MONGO_TIMEOUT_MS = 5000


def _should_use_local() -> bool:
    return os.getenv("USE_LOCAL_DATA", "false").lower() in ("1", "true", "yes")


def is_local_mode() -> bool:
    """True when using in-memory JSON fallback instead of MongoDB."""
    get_database()
    return _use_local or _should_use_local()


def _load_local_data() -> None:
    """Load seed JSON files into memory for offline/demo mode."""
    global _local_products, _local_sales, _use_local
    products_path = DATA_DIR / "seed_products.json"
    sales_path = DATA_DIR / "seed_sales.json"
    with open(products_path, encoding="utf-8") as f:
        _local_products = json.load(f)
    with open(sales_path, encoding="utf-8") as f:
        _local_sales = json.load(f)
    _use_local = True
    logger.info("Using local JSON data store (USE_LOCAL_DATA=true)")


def _reset_client() -> None:
    global _mongo_client, _db
    if _mongo_client is not None:
        try:
            _mongo_client.close()
        except Exception:
            pass
    _mongo_client = None
    _db = None


def _production_connection_error(message: str, cause: Exception | None = None) -> None:
    detail = (
        f"{message} "
        "Set MONGO_URI to a valid Atlas connection string or set USE_LOCAL_DATA=true for local JSON only."
    )
    if cause is not None:
        raise RuntimeError(detail) from cause
    raise RuntimeError(detail)


def _create_mongo_client() -> MongoClient:
    """Create MongoClient, ping immediately, and cache as singleton."""
    global _mongo_client

    import certifi
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri or "<user>" in mongo_uri:
        _production_connection_error("MONGO_URI is missing or not configured.")

    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
            connectTimeoutMS=MONGO_TIMEOUT_MS,
            socketTimeoutMS=MONGO_TIMEOUT_MS,
            tls=True,
            tlsCAFile=certifi.where(),
            maxPoolSize=10,
        )
        client.admin.command("ping")
        _mongo_client = client
        logger.info("Connected to MongoDB Atlas (ping ok)")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        _reset_client()
        _production_connection_error("MongoDB connection failed on startup.", exc)
    except Exception as exc:
        _reset_client()
        _production_connection_error("MongoDB connection failed on startup.", exc)


def get_mongo_client() -> MongoClient | None:
    """Return cached MongoClient singleton; None when USE_LOCAL_DATA=true."""
    global _mongo_client

    if _should_use_local():
        return None

    if _mongo_client is not None:
        try:
            _mongo_client.admin.command("ping")
            return _mongo_client
        except Exception:
            logger.warning("MongoDB client stale — reconnecting")
            _reset_client()

    return _create_mongo_client()


def get_database() -> Database | None:
    """Return the application database handle."""
    global _db, _use_local

    if _use_local or _should_use_local():
        if not _local_products:
            _load_local_data()
        return None

    client = get_mongo_client()
    if client is None:
        _load_local_data()
        return None

    if _db is None:
        db_name = os.getenv("MONGO_DB_NAME", "festival_bundle_agent")
        _db = client[db_name]
    return _db


def get_collection(name: str) -> Collection | None:
    """Return a MongoDB collection by name."""
    db = get_database()
    if db is None:
        return None
    return db[name]


def get_products_collection() -> Collection | None:
    return get_collection("products")


def get_sales_collection() -> Collection | None:
    return get_collection("sales_history")


def find_products(query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Query products from MongoDB or local store."""
    query = query or {}
    collection = get_products_collection()
    if collection is not None:
        return list(collection.find(query, {"_id": 0}))
    if not _local_products:
        _load_local_data()
    results = _local_products.copy()
    if "category" in query:
        results = [p for p in results if p.get("category") == query["category"]]
    if "stock_quantity" in query:
        op = query["stock_quantity"]
        if isinstance(op, dict):
            if "$gt" in op:
                results = [p for p in results if p["stock_quantity"] > op["$gt"]]
            if "$lt" in op:
                results = [p for p in results if p["stock_quantity"] < op["$lt"]]
            if "$gte" in op:
                results = [p for p in results if p["stock_quantity"] >= op["$gte"]]
            if "$lte" in op:
                results = [p for p in results if p["stock_quantity"] <= op["$lte"]]
    if "name" in query:
        name_query = query["name"]
        if isinstance(name_query, dict) and "$in" in name_query:
            names = set(name_query["$in"])
            results = [p for p in results if p["name"] in names]
        else:
            results = [p for p in results if p["name"] == name_query]
    return results


def find_product_by_name(name: str) -> dict[str, Any] | None:
    """Look up a single product by name."""
    products = find_products({"name": name})
    return products[0] if products else None


def find_all_products() -> list[dict[str, Any]]:
    return find_products({})


def check_health() -> bool:
    """Ping MongoDB or verify local data is loaded."""
    if _should_use_local():
        _load_local_data()
        return len(_local_products) > 0

    try:
        client = get_mongo_client()
        if client is None:
            return False
        client.admin.command("ping")
        return True
    except Exception as exc:
        logger.error("Database health check failed", extra={"extra_data": {"error": str(exc)}})
        _reset_client()
        return False
