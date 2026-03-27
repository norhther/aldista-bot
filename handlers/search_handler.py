"""Search command: inline search with paginated results."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import catalog as cat
import config
import ui

WAITING_QUERY = 1
_MAX_RESULTS = 20


def _results_text_and_markup(results: list[dict], query: str) -> tuple[str, InlineKeyboardMarkup]:
    if not results:
        text = (
            f"🔍 <b>Sin resultados</b>\n"
            f"{ui.divider()}\n"
            f"No encontré nada para <i>{ui.e(query)}</i>.\n"
            "Prueba con otra palabra clave."
        )
        return text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")]
        ])

    shown = results[:_MAX_RESULTS]
    in_stock_count = sum(1 for p in results if p["stock_status"] == "in_stock")

    lines = [
        f"🔍 <b>Resultados para «{ui.e(query)}»</b>",
        f"<i>{len(results)} encontrados  ·  {in_stock_count} en stock</i>",
        ui.divider(),
    ]
    for i, p in enumerate(shown, 1):
        lines.append(ui.product_row(p, index=i))

    if len(results) > _MAX_RESULTS:
        lines.append(f"\n<i>Mostrando {_MAX_RESULTS} de {len(results)}. Afina la búsqueda.</i>")

    keyboard = [
        [InlineKeyboardButton(
            f"{'🟢' if p['stock_status'] == 'in_stock' else '🔴'}  {p['name'][:38]}",
            callback_data=f"detail:{p['product_id']}:search_back:{i}",
        )]
        for i, p in enumerate(shown, 1)
    ]
    keyboard.append([InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")])

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        query = " ".join(context.args)
        results = cat.search(query)
        text, markup = _results_text_and_markup(results, query)
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 <b>Buscar tabaco</b>\n"
        f"{ui.divider()}\n"
        "Escribe el <b>nombre</b>, <b>marca</b> o <b>referencia</b> que buscas.\n"
        "<i>Puedes cancelar con /cancel</i>",
        parse_mode="HTML",
    )
    return WAITING_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    results = cat.search(query)
    text, markup = _results_text_and_markup(results, query)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Búsqueda cancelada.", parse_mode="HTML")
    return ConversationHandler.END


def build_search_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("search", search_cmd)],
        states={
            WAITING_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
