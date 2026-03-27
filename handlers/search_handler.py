"""Search command and inline search flow."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import catalog as cat
import config

WAITING_QUERY = 1


def _results_markup(results: list[dict], query: str) -> tuple[str, InlineKeyboardMarkup]:
    if not results:
        return f'🔍 Sin resultados para "*{query}*".', InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 Menú", callback_data="menu:main")]]
        )

    shown = results[: config.PAGE_SIZE * 2]
    lines = [f'🔍 *{len(results)}* resultado(s) para "*{query}*":\n']
    keyboard = []
    for p in shown:
        icon = "✅" if p["stock_status"] == "in_stock" else "❌"
        new_tag = " 🆕" if p.get("is_new") else ""
        lines.append(f"{icon} *{p['name']}*{new_tag} — {p['price']}")
        keyboard.append([
            InlineKeyboardButton(
                f"🔎 {p['name'][:30]}", callback_data=f"detail:{p['product_id']}"
            )
        ])

    if len(results) > len(shown):
        lines.append(f"\n_...y {len(results) - len(shown)} más. Afina la búsqueda._")

    keyboard.append([InlineKeyboardButton("🏠 Menú", callback_data="menu:main")])
    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        query = " ".join(context.args)
        results = cat.search(query)
        text, markup = _results_markup(results, query)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        return ConversationHandler.END

    await update.message.reply_text(
        "🔍 ¿Qué tabaco buscas? Escribe el nombre, marca o referencia:"
    )
    return WAITING_QUERY


async def receive_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    results = cat.search(query)
    text, markup = _results_markup(results, query)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Búsqueda cancelada.")
    return ConversationHandler.END


def build_search_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("search", search_cmd)],
        states={
            WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_query)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
