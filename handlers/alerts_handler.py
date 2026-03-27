"""Alert management: add, list, cancel alerts per user."""

from __future__ import annotations

import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import catalog as cat

_STATE_FILE = Path(__file__).parent.parent / "alerts_state.json"
WAITING_ALERT_QUERY = 10


# ── Persistence helpers ───────────────────────────────────────────────────────

def _load() -> dict[str, list[str]]:
    """Returns {str(user_id): [product_id, ...]}"""
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {}


def _save(state: dict[str, list[str]]) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def user_alerts(user_id: int) -> list[str]:
    return _load().get(str(user_id), [])


def add_alert(user_id: int, product_id: str) -> bool:
    """Returns True if added, False if already existed."""
    state = _load()
    key = str(user_id)
    alerts = state.setdefault(key, [])
    if product_id in alerts:
        return False
    alerts.append(product_id)
    _save(state)
    return True


def remove_alert(user_id: int, product_id: str) -> bool:
    state = _load()
    key = str(user_id)
    if product_id not in state.get(key, []):
        return False
    state[key].remove(product_id)
    _save(state)
    return True


def all_alerts() -> dict[str, list[str]]:
    return _load()


# ── Command handlers ──────────────────────────────────────────────────────────

async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        query = " ".join(context.args)
        return await _handle_alert_query(update, query)

    await update.message.reply_text(
        "🔔 ¿Para qué tabaco quieres una alerta? Escribe el nombre o marca:"
    )
    return WAITING_ALERT_QUERY


async def receive_alert_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_alert_query(update, update.message.text.strip())


async def _handle_alert_query(update: Update, query: str) -> int:
    results = cat.search(query)
    oos = [p for p in results if p["stock_status"] == "out_of_stock"]

    if not results:
        await update.message.reply_text(f'❌ Sin resultados para "*{query}*".', parse_mode="Markdown")
        return ConversationHandler.END

    if not oos:
        await update.message.reply_text(
            f'✅ Todos los resultados para "*{query}*" están en stock. ¡No necesitas alerta!',
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(
            f"🔔 {p['name'][:35]}",
            callback_data=f"alert_add:{p['product_id']}",
        )]
        for p in oos[:10]
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu:main")])

    await update.message.reply_text(
        f"🔔 Productos agotados que coinciden con *{query}*.\nElige uno para crear la alerta:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


async def myalerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    ids = user_alerts(user_id)
    if not ids:
        await update.message.reply_text("📭 No tienes alertas activas.")
        return
    await _show_alerts(update.message, user_id, ids)


async def cancel_alert_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END


async def _show_alerts(message, user_id: int, ids: list[str]) -> None:
    lines = ["🔔 *Tus alertas activas:*\n"]
    keyboard = []
    for pid in ids:
        p = cat.get_by_id(pid)
        if p:
            icon = "✅" if p["stock_status"] == "in_stock" else "❌"
            lines.append(f"{icon} {p['name']} — {p['price']}")
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 Eliminar: {p['name'][:28]}",
                    callback_data=f"alert_del:{pid}",
                )
            ])
        else:
            lines.append(f"⚠️ Producto {pid} no encontrado")
            keyboard.append([
                InlineKeyboardButton(f"🗑 Eliminar {pid}", callback_data=f"alert_del:{pid}")
            ])
    keyboard.append([InlineKeyboardButton("🏠 Menú", callback_data="menu:main")])
    await message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ── Callback handlers (registered in main.py) ────────────────────────────────

async def cb_alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]
    user_id = update.effective_user.id
    p = cat.get_by_id(product_id)

    if not p:
        await query.edit_message_text("❌ Producto no encontrado.")
        return

    added = add_alert(user_id, product_id)
    if added:
        text = (
            f"✅ Alerta creada para:\n*{p['name']}*\n\n"
            "Te avisaré cuando vuelva a estar en stock."
        )
    else:
        text = f"ℹ️ Ya tienes una alerta para *{p['name']}*."

    keyboard = [[InlineKeyboardButton("🔔 Mis alertas", callback_data="menu:alerts"),
                 InlineKeyboardButton("🏠 Menú", callback_data="menu:main")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_alert_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]
    user_id = update.effective_user.id
    removed = remove_alert(user_id, product_id)
    p = cat.get_by_id(product_id)
    name = p["name"] if p else product_id
    msg = f"🗑 Alerta eliminada: *{name}*" if removed else "ℹ️ Alerta no encontrada."
    await query.edit_message_text(msg, parse_mode="Markdown")


def build_alert_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("alert", alert_cmd)],
        states={
            WAITING_ALERT_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_alert_query)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_alert_conv)],
    )
