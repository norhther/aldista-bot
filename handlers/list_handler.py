"""Paginated catalog listing, brand filtering, product detail, stats."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import catalog as cat
import config
import ui


# ── Page builder ─────────────────────────────────────────────────────────────

def _build_page(
    products: list[dict],
    page: int,
    nav_prefix: str,
    title: str = "Catálogo",
) -> tuple[str, InlineKeyboardMarkup]:
    total_pages = max(1, (len(products) + config.PAGE_SIZE - 1) // config.PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * config.PAGE_SIZE
    chunk = products[start: start + config.PAGE_SIZE]

    in_stock = sum(1 for p in products if p["stock_status"] == "in_stock")
    lines = [
        f"📋 <b>{ui.e(title)}</b>  "
        f"<i>({in_stock}/{len(products)} disponibles)</i>\n"
        f"<i>Página {page} de {total_pages}</i>\n"
        f"{ui.divider()}",
    ]

    item_buttons: list[InlineKeyboardButton] = []
    for i, p in enumerate(chunk, start=start + 1):
        lines.append(ui.product_row(p, index=i))
        label = p["name"][:32]
        item_buttons.append(
            InlineKeyboardButton(label, callback_data=f"detail:{p['product_id']}:{nav_prefix}:{page}")
        )

    # Item buttons: one per row (full width, readable name)
    keyboard: list[list[InlineKeyboardButton]] = [[btn] for btn in item_buttons]

    # Navigation row
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️  Anterior", callback_data=f"{nav_prefix}:{page - 1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Siguiente  ▶️", callback_data=f"{nav_prefix}:{page + 1}"))
    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")])

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


# ── Command handlers ──────────────────────────────────────────────────────────

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = cat.get_products()
    text, markup = _build_page(products, 1, "menu:list")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def brands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_brands(update.message.reply_text)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _stats_text()
    await update.message.reply_text(text, parse_mode="HTML")


async def oos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = [p for p in cat.get_products() if p["stock_status"] == "out_of_stock"]
    text, markup = _build_page(products, 1, "menu:oos", title="Agotados")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def cb_oos_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    products = [p for p in cat.get_products() if p["stock_status"] == "out_of_stock"]
    text, markup = _build_page(products, page, "menu:oos", title="Agotados")
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def novedades_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = cat.get_novedades()
    if not products:
        await update.message.reply_text(
            "✨ <b>Sin novedades</b>\n"
            f"{ui.divider()}\n"
            "No hay productos nuevos en el último mes.",
            parse_mode="HTML",
        )
        return
    text, markup = _build_page(products, 1, "menu:novedades", title="Novedades — nuevos en catálogo")
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ── Shared renderers ──────────────────────────────────────────────────────────

def _stats_text() -> str:
    stats = cat.catalog_stats()
    pct = round(stats["in_stock"] / stats["total"] * 100) if stats["total"] else 0
    brands = cat.get_brands()
    return (
        f"📊 <b>Estadísticas del catálogo</b>\n"
        f"{ui.divider()}\n"
        f"🗂  Total:       <b>{stats['total']}</b> productos\n"
        f"🟢  En stock:    <b>{stats['in_stock']}</b> ({pct}%)\n"
        f"🔴  Agotados:   <b>{stats['out_of_stock']}</b>\n"
        f"🏷  Marcas:      <b>{len(brands)}</b>\n"
        f"{ui.divider()}\n"
        f"<i>🕐 {ui.e(stats['updated_at'])}</i>"
    )


async def _send_brands(send_fn) -> None:
    brands = cat.get_brands()
    all_products = cat.get_products()

    keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(brands), 2):
        row = []
        for brand in brands[i: i + 2]:
            count = sum(1 for p in all_products if p["brand"] == brand)
            in_s = sum(1 for p in all_products if p["brand"] == brand and p["stock_status"] == "in_stock")
            row.append(
                InlineKeyboardButton(
                    f"{brand}  ({in_s}/{count})",
                    callback_data=f"brand:{brand}:1",
                )
            )
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")])
    await send_fn(
        f"🏷  <b>{len(brands)} marcas disponibles</b>\n"
        "<i>Formato: nombre  (en stock / total)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Callback handlers ─────────────────────────────────────────────────────────

async def cb_list_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    products = cat.get_products()
    text, markup = _build_page(products, page, "menu:list")
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def cb_novedades_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[-1])
    products = cat.get_novedades()
    if not products:
        await query.edit_message_text(
            "✨ <b>Sin novedades</b>\n"
            f"{ui.divider()}\n"
            "No hay productos nuevos en el último mes.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")]
            ]),
        )
        return
    text, markup = _build_page(products, page, "menu:novedades", title="Novedades — nuevos en catálogo")
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def cb_brand_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")   # brand:<name>:<page>
    brand_name = parts[1]
    page = int(parts[2])
    products = [p for p in cat.get_products() if p["brand"] == brand_name]
    text, markup = _build_page(products, page, f"brand:{brand_name}", title=brand_name)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


async def cb_brands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    brands = cat.get_brands()
    all_products = cat.get_products()

    keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(brands), 2):
        row = []
        for brand in brands[i: i + 2]:
            count = sum(1 for p in all_products if p["brand"] == brand)
            in_s = sum(1 for p in all_products if p["brand"] == brand and p["stock_status"] == "in_stock")
            row.append(
                InlineKeyboardButton(
                    f"{brand}  ({in_s}/{count})",
                    callback_data=f"brand:{brand}:1",
                )
            )
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")])
    await query.edit_message_text(
        f"🏷  <b>{len(brands)} marcas disponibles</b>\n"
        "<i>Formato: nombre  (en stock / total)</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cb_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        _stats_text(),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")]
        ]),
    )


async def cb_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # callback_data format: detail:<product_id>:<nav_prefix>:<page>
    parts = query.data.split(":")
    product_id = parts[1]
    # Reconstruct nav_prefix (may contain colons, e.g. "brand:Al Waha")
    nav_prefix = ":".join(parts[2:-1]) if len(parts) > 3 else "menu:list"
    page = parts[-1] if len(parts) > 2 else "1"

    p = cat.get_by_id(product_id)
    if not p:
        await query.edit_message_text("❌ Producto no encontrado.")
        return

    text = (
        f"{ui.product_card(p)}\n"
        f"{ui.divider()}\n"
        f'🔗 <a href="{ui.e(p["url"])}">Ver en tienda →</a>'
    )

    back_data = nav_prefix if page == "0" else f"{nav_prefix}:{page}"
    buttons = []
    if p["stock_status"] == "out_of_stock":
        buttons.append(
            InlineKeyboardButton("🔔  Alertar cuando vuelva", callback_data=f"alert_add:{product_id}")
        )
    keyboard = (
        [[btn] for btn in buttons]
        + [[
            InlineKeyboardButton("◀️  Volver", callback_data=back_data),
            InlineKeyboardButton("🏠  Inicio", callback_data="menu:main"),
        ]]
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )
