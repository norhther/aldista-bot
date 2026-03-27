from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import catalog as cat


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = cat.catalog_stats()
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver catálogo", callback_data="menu:list:1"),
            InlineKeyboardButton("🔍 Buscar", callback_data="menu:search"),
        ],
        [
            InlineKeyboardButton("🔔 Mis alertas", callback_data="menu:alerts"),
            InlineKeyboardButton("📊 Estadísticas", callback_data="menu:stats"),
        ],
    ]
    text = (
        "👋 *Bienvenido al bot de Aldista Tobacco*\n\n"
        f"🗂 *{stats['total']}* productos  |  "
        f"✅ *{stats['in_stock']}* en stock  |  "
        f"❌ *{stats['out_of_stock']}* agotados\n"
        f"🕐 Actualizado: {stats['updated_at']}\n\n"
        "¿Qué quieres hacer?"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🤖 *Comandos disponibles:*\n\n"
        "/start — Menú principal\n"
        "/list — Ver catálogo completo\n"
        "/search \\<texto\\> — Buscar tabaco\n"
        "/brands — Ver marcas disponibles\n"
        "/alert \\<texto\\> — Crear alerta de reposición\n"
        "/myalerts — Ver y cancelar tus alertas\n"
        "/stats — Estadísticas del catálogo\n"
        "/help — Esta ayuda\n"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2")
