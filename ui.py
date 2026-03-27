"""Shared UI helpers: HTML formatting and card builders."""

from __future__ import annotations

import html
from typing import Any


def e(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return html.escape(str(text))


def stock_badge(product: dict) -> str:
    if product["stock_status"] == "in_stock":
        return "🟢 En stock"
    return "🔴 Agotado"


def new_badge(product: dict) -> str:
    return " ✨<b>NUEVO</b>" if product.get("is_new") else ""


def product_card(p: dict) -> str:
    """Full detail card for a single product."""
    badge = stock_badge(p)
    new = new_badge(p)
    return (
        f"<b>{e(p['name'])}</b>{new}\n"
        f"├ 🏷  <b>{e(p['brand'])}</b>\n"
        f"├ 📦  <code>{e(p['reference'])}</code>\n"
        f"├ 💶  <b>{e(p['price'])}</b>\n"
        f"└ {badge}"
    )


def product_row(p: dict, index: int | None = None) -> str:
    """Compact one-liner for list/search views."""
    icon = "🟢" if p["stock_status"] == "in_stock" else "🔴"
    new = " ✨" if p.get("is_new") else ""
    prefix = f"{index}. " if index is not None else ""
    return f"{prefix}{icon} {e(p['name'])}{new}  —  <b>{e(p['price'])}</b>"


def divider() -> str:
    return "─────────────────────"


def header(title: str, subtitle: str = "") -> str:
    sub = f"\n<i>{e(subtitle)}</i>" if subtitle else ""
    return f"<b>{e(title)}</b>{sub}"
