from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import catalog as cat
import ui
import users


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    novedades = cat.get_novedades()
    nov_label = f"✨  Novedades ({len(novedades)})" if novedades else "✨  Novedades"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋  Catálogo", callback_data="menu:list:1"),
            InlineKeyboardButton("🏷  Marcas", callback_data="menu:brands"),
        ],
        [
            InlineKeyboardButton(nov_label, callback_data="menu:novedades:1"),
            InlineKeyboardButton("🔍  Buscar", callback_data="menu:search"),
        ],
        [
            InlineKeyboardButton("🔴  Agotados", callback_data="menu:oos:1"),
            InlineKeyboardButton("🔔  Mis alertas", callback_data="menu:alerts"),
        ],
    ])


def _main_menu_text() -> str:
    stats = cat.catalog_stats()
    pct = round(stats["in_stock"] / stats["total"] * 100) if stats["total"] else 0
    bar_filled = round(pct / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    return (
        f"<code>{bar}</code>  {pct}%\n"
        f"🗂  <b>{stats['total']}</b> productos   "
        f"🟢 <b>{stats['in_stock']}</b> disponibles   "
        f"🔴 <b>{stats['out_of_stock']}</b> agotados\n"
        f"<i>🕐 Actualizado: {ui.e(stats['updated_at'])}</i>\n"
        f"{ui.divider()}\n"
        "¿Qué quieres hacer?"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users.register(update.effective_user.id)
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
        "/novedades — Productos nuevos (último mes)\n"
        "/search — Buscar tabaco\n"
        "/alert — Crear alerta de reposición\n"
        "/myalerts — Gestionar tus alertas\n"
        "/help — Esta ayuda"
    )
    await update.message.reply_text(text, parse_mode="HTML")
