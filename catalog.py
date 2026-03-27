"""Fetches and caches the Aldista catalog from the GitHub Pages JSON."""

from __future__ import annotations

import time
from typing import Any

import requests

import config

_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 15 * 60  # 15 minutes


def fetch_catalog(force: bool = False) -> dict[str, Any]:
    global _cache, _cache_ts
    if not force and _cache and (time.time() - _cache_ts) < _CACHE_TTL:
        return _cache
    resp = requests.get(config.CATALOG_URL, timeout=15)
    resp.raise_for_status()
    _cache = resp.json()
    _cache_ts = time.time()
    return _cache


def _by_id_desc(products: list[dict]) -> list[dict]:
    return sorted(products, key=lambda p: int(p["product_id"]), reverse=True)


def get_products(force: bool = False) -> list[dict]:
    return _by_id_desc(fetch_catalog(force).get("products", []))


def get_novedades() -> list[dict]:
    """Products first seen within the last 30 days (is_new flag set by scraper)."""
    return [p for p in get_products() if p.get("is_new")]


def get_brands() -> list[str]:
    seen: set[str] = set()
    brands: list[str] = []
    for p in get_products():
        b = p["brand"]
        if b not in seen:
            seen.add(b)
            brands.append(b)
    return sorted(brands)


def search(query: str) -> list[dict]:
    q = query.lower()
    return [
        p for p in get_products()
        if q in p["name"].lower() or q in p["brand"].lower() or q in p["reference"].lower()
    ]


def get_by_id(product_id: str) -> dict | None:
    for p in get_products():
        if p["product_id"] == product_id:
            return p
    return None


def catalog_stats() -> dict[str, Any]:
    data = fetch_catalog()
    return {
        "total": data.get("total", 0),
        "in_stock": data.get("in_stock", 0),
        "out_of_stock": data.get("out_of_stock", 0),
        "updated_at": data.get("updated_at", "?"),
    }
