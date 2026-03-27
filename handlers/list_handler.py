"""Paginated catalog listing, optionally filtered by brand."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import catalog as cat
import config


def _product_row(p: dict) -> str:
    icon = "✅" if p["stock_status"] == "in_stock" else "❌"
    new_tag = " 🆕" if p.get("is_new") else ""
    return f"{icon} *{p['name']}*{new_tag}\n   💶 {p['price']}  |  📦 `{p['reference']}`"


def _build_page(products: list[dict], page: int, prefix: str) -> tuple[str, InlineKeyboardMarkup]:
    total_pages = max(1, (len(products) + config.PAGE_SIZE - 1) // config.PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * config.PAGE_SIZE
    chunk = products[start: start + config.PAGE_SIZE]

    lines = [f"📋 Página {page}/{total_pages} — {len(products)} productos\n"]
    buttons_row: list[InlineKeyboardButton] = []

    for p in chunk:
        lines.append(_product_row(p))
        buttons_row.append(
            InlineKeyboardButton(
                f"🔗 {p['brand'][:12]}", callback_data=f"detail:{p['product_id']}"
            )
        )

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}:{page + 1}"))

    keyboard = []
    # Group detail buttons in rows of 2
    for i in range(0, len(buttons_row), 2):
        keyboard.append(buttons_row[i: i + 2])
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🏠 Menú", callback_data="menu:main")])

    return "\n\n".join(lines), InlineKeyboardMarkup(keyboard)


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = cat.get_products()
    text, markup = _build_page(products, 1, "menu:list")
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def brands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    brands = cat.get_brands()
    keyboard = []
    for i in range(0, len(brands), 2):
        row = [
            InlineKeyboardButton(brands[i], callback_data=f"brand:{brands[i]}:1"),
        ]
        if i + 1 < len(brands):
            row.append(InlineKeyboardButton(brands[i + 1], callback_data=f"brand:{brands[i + 1]}:1"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🏠 Menú", callback_data="menu:main")])
    await update.message.reply_text(
        f"🏷️ *{len(brands)} marcas disponibles:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = cat.catalog_stats()
    pct = round(stats["in_stock"] / stats["total"] * 100) if stats["total"] else 0
    text = (
        "📊 *Estadísticas del catálogo*\n\n"
        f"🗂 Total: *{stats['total']}*\n"
        f"✅ En stock: *{stats['in_stock']}* ({pct}%)\n"
        f"❌ Agotados: *{stats['out_of_stock']}*\n"
        f"🕐 Última actualización: {stats['updated_at']}"
    )
    await (update.message or update.callback_query.message).reply_text(
        text, parse_mode="Markdown"
    )


# ── Callback handlers ────────────────────────────────────────────────────────

async def cb_list_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, page_str = query.data.split(":")
    products = cat.get_products()
    text, markup = _build_page(products, int(page_str), "menu:list")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


async def cb_brand_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")  # brand:<name>:<page>
    brand_name = parts[1]
    page = int(parts[2])
    products = [p for p in cat.get_products() if p["brand"] == brand_name]
    text, markup = _build_page(products, page, f"brand:{brand_name}")
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)


async def cb_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]
    p = cat.get_by_id(product_id)
    if not p:
        await query.edit_message_text("❌ Producto no encontrado.")
        return

    icon = "✅ En stock" if p["stock_status"] == "in_stock" else "❌ Agotado"
    new_tag = "🆕 Nuevo  |  " if p.get("is_new") else ""
    text = (
        f"🪴 *{p['name']}*\n\n"
        f"🏷️ Marca: {p['brand']}\n"
        f"📦 Ref: `{p['reference']}`\n"
        f"💶 Precio: *{p['price']}*\n"
        f"📊 {new_tag}{icon}\n"
        f"🔗 [Ver en tienda]({p['url']})"
    )
    keyboard = [[
        InlineKeyboardButton("🔔 Alertar si vuelve", callback_data=f"alert_add:{product_id}"),
        InlineKeyboardButton("⬅️ Volver", callback_data="menu:list:1"),
    ]]
    await query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )
