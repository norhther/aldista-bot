"""Alert management: add, list, cancel back-in-stock alerts per user."""

from __future__ import annotations

import json
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

import catalog as cat
import ui

_STATE_FILE = Path(__file__).parent.parent / "alerts_state.json"
WAITING_ALERT_QUERY = 10


# ── Persistence ───────────────────────────────────────────────────────────────

def _load() -> dict[str, list[str]]:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text())
    return {}


def _save(state: dict[str, list[str]]) -> None:
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def user_alerts(user_id: int) -> list[str]:
    return _load().get(str(user_id), [])


def add_alert(user_id: int, product_id: str) -> bool:
    state = _load()
    alerts = state.setdefault(str(user_id), [])
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


# ── Shared renderers ──────────────────────────────────────────────────────────

def _alerts_text_and_markup(ids: list[str]) -> tuple[str, InlineKeyboardMarkup]:
    lines = [
        f"🔔 <b>Tus alertas activas</b>",
        f"<i>Te avisaremos cuando vuelvan al stock.</i>",
        ui.divider(),
    ]
    keyboard: list[list[InlineKeyboardButton]] = []

    for pid in ids:
        p = cat.get_by_id(pid)
        if p:
            badge = "🟢" if p["stock_status"] == "in_stock" else "🔴"
            lines.append(f"{badge} {ui.e(p['name'])}  —  <b>{ui.e(p['price'])}</b>")
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑  {p['name'][:36]}",
                    callback_data=f"alert_del:{pid}",
                )
            ])
        else:
            lines.append(f"⚠️  Producto <code>{ui.e(pid)}</code> no encontrado")
            keyboard.append([
                InlineKeyboardButton(f"🗑  Eliminar {pid}", callback_data=f"alert_del:{pid}")
            ])

    keyboard.append([InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")])
    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


def _no_alerts_text_and_markup() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "🔔 <b>Sin alertas activas</b>\n"
        f"{ui.divider()}\n"
        "No tienes ninguna alerta configurada.\n"
        "Busca un tabaco agotado y pulsa <i>Alertar cuando vuelva</i>."
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍  Buscar tabaco", callback_data="menu:search")],
        [InlineKeyboardButton("🏠  Inicio", callback_data="menu:main")],
    ])
    return text, markup


# ── Command handlers ──────────────────────────────────────────────────────────

async def alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.args:
        return await _handle_alert_query(update, " ".join(context.args))
    await update.message.reply_text(
        "🔔 <b>Nueva alerta</b>\n"
        f"{ui.divider()}\n"
        "Escribe el nombre o marca del tabaco para el que quieres la alerta.\n"
        "<i>Solo podrás alertar tabacos agotados.</i>\n"
        "<i>Cancela con /cancel</i>",
        parse_mode="HTML",
    )
    return WAITING_ALERT_QUERY


async def receive_alert_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_alert_query(update, update.message.text.strip())


async def _handle_alert_query(update: Update, query: str) -> int:
    results = cat.search(query)
    oos = [p for p in results if p["stock_status"] == "out_of_stock"]

    if not results:
        await update.message.reply_text(
            f"❌ <b>Sin resultados</b>\n"
            f"{ui.divider()}\n"
            f"No encontré nada para <i>{ui.e(query)}</i>.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    if not oos:
        in_stock_names = ", ".join(ui.e(p["name"][:20]) for p in results[:3])
        await update.message.reply_text(
            f"✅ <b>¡Todo en stock!</b>\n"
            f"{ui.divider()}\n"
            f"Los resultados para <i>{ui.e(query)}</i> están disponibles:\n"
            f"<i>{in_stock_names}…</i>\n\n"
            "No necesitas crear ninguna alerta.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    lines = [
        f"🔔 <b>Alertas para «{ui.e(query)}»</b>",
        f"<i>{len(oos)} agotado(s) encontrado(s). Elige cuál añadir:</i>",
        ui.divider(),
    ]
    for p in oos[:10]:
        lines.append(f"🔴 {ui.e(p['name'])}  —  <b>{ui.e(p['price'])}</b>")

    keyboard = [
        [InlineKeyboardButton(
            f"🔔  {p['name'][:38]}",
            callback_data=f"alert_add:{p['product_id']}",
        )]
        for p in oos[:10]
    ]
    keyboard.append([InlineKeyboardButton("❌  Cancelar", callback_data="menu:main")])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


async def myalerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ids = user_alerts(update.effective_user.id)
    if not ids:
        text, markup = _no_alerts_text_and_markup()
    else:
        text, markup = _alerts_text_and_markup(ids)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


async def cancel_alert_conv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END


# ── Callback handlers ─────────────────────────────────────────────────────────

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
            f"✅ <b>Alerta creada</b>\n"
            f"{ui.divider()}\n"
            f"{ui.product_card(p)}\n"
            f"{ui.divider()}\n"
            "Te notificaremos en cuanto vuelva al stock. 🎯"
        )
    else:
        text = (
            f"ℹ️ <b>Alerta ya existente</b>\n"
            f"{ui.divider()}\n"
            f"Ya tienes una alerta activa para:\n<i>{ui.e(p['name'])}</i>"
        )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔔  Mis alertas", callback_data="menu:alerts"),
                InlineKeyboardButton("🏠  Inicio", callback_data="menu:main"),
            ]
        ]),
    )


async def cb_alert_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]
    user_id = update.effective_user.id
    p = cat.get_by_id(product_id)
    name = p["name"] if p else product_id

    remove_alert(user_id, product_id)

    # Refresh the alerts list in-place
    remaining = user_alerts(user_id)
    if remaining:
        text, markup = _alerts_text_and_markup(remaining)
        header = f"🗑  <b>Alerta eliminada:</b> <i>{ui.e(name)}</i>\n\n" + text
        await query.edit_message_text(header, parse_mode="HTML", reply_markup=markup)
    else:
        text, markup = _no_alerts_text_and_markup()
        await query.edit_message_text(
            f"🗑  <b>Alerta eliminada</b>\n\n{text}",
            parse_mode="HTML",
            reply_markup=markup,
        )


async def cb_alerts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show alerts list via callback (from menu button)."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ids = user_alerts(user_id)
    if not ids:
        text, markup = _no_alerts_text_and_markup()
    else:
        text, markup = _alerts_text_and_markup(ids)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)


def build_alert_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("alert", alert_cmd)],
        states={
            WAITING_ALERT_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_alert_query)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_alert_conv)],
    )
