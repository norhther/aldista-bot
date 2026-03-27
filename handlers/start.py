from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import catalog as cat
import ui


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋  Catálogo", callback_data="menu:list:1"),
            InlineKeyboardButton("🏷  Marcas", callback_data="menu:brands"),
        ],
        [
            InlineKeyboardButton("🔍  Buscar", callback_data="menu:search"),
            InlineKeyboardButton("📊  Stats", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("🔔  Mis alertas", callback_data="menu:alerts"),
        ],
    ])


def _main_menu_text() -> str:
    stats = cat.catalog_stats()
    pct = round(stats["in_stock"] / stats["total"] * 100) if stats["total"] else 0
    bar_filled = round(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    return (
        "🪴 <b>Aldista Tobacco Bot</b>\n"
        f"{ui.divider()}\n"
        f"<code>{bar}</code>  {pct}%\n"
        f"🗂  <b>{stats['total']}</b> productos   "
        f"🟢 <b>{stats['in_stock']}</b> disponibles   "
        f"🔴 <b>{stats['out_of_stock']}</b> agotados\n"
        f"<i>🕐 Actualizado: {ui.e(stats['updated_at'])}</i>\n"
        f"{ui.divider()}\n"
        "¿Qué quieres hacer?"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        _main_menu_text(),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        _main_menu_text(),
        parse_mode="HTML",
        reply_markup=_main_menu_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 <b>Comandos disponibles</b>\n"
        f"{ui.divider()}\n"
        "/start — Menú principal\n"
        "/list — Catálogo completo\n"
        "/brands — Ver marcas\n"
        "/search — Buscar tabaco\n"
        "/alert — Crear alerta de reposición\n"
        "/myalerts — Gestionar tus alertas\n"
        "/stats — Estadísticas\n"
        "/help — Esta ayuda"
    )
    await update.message.reply_text(text, parse_mode="HTML")
