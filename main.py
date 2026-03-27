"""Aldista Tobacco Telegram Bot — entry point."""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
)

import config
from handlers.start import start, help_cmd
from handlers.list_handler import (
    list_cmd,
    brands_cmd,
    stats_cmd,
    cb_list_page,
    cb_brand_page,
    cb_detail,
)
from handlers.search_handler import build_search_conversation
from handlers.alerts_handler import (
    myalerts_cmd,
    cb_alert_add,
    cb_alert_del,
    build_alert_conversation,
)
from jobs.stock_checker import check_stock

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cb_main_menu(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
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
    await query.edit_message_text(
        "🏠 *Menú principal* — ¿Qué quieres hacer?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cb_menu_router(update: Update, context) -> None:
    query = update.callback_query
    parts = query.data.split(":")
    action = parts[1]

    if action == "main":
        await cb_main_menu(update, context)
    elif action == "list":
        await cb_list_page(update, context)
    elif action == "stats":
        await query.answer()
        await stats_cmd(update, context)
    elif action == "alerts":
        await query.answer()
        from handlers.alerts_handler import all_alerts, _show_alerts
        user_id = update.effective_user.id
        ids = all_alerts().get(str(user_id), [])
        if not ids:
            await query.edit_message_text("📭 No tienes alertas activas.")
        else:
            await query.message.delete()
            await _show_alerts(query.message, user_id, ids)
    elif action == "search":
        await query.answer()
        await query.edit_message_text("🔍 Usa /search <texto> para buscar un tabaco.")


def main() -> None:
    app: Application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_TOKEN)
        .build()
    )

    # ── Conversation handlers (must be added before plain command handlers)
    app.add_handler(build_search_conversation())
    app.add_handler(build_alert_conversation())

    # ── Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("brands", brands_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("myalerts", myalerts_cmd))

    # ── Callback query handlers
    app.add_handler(CallbackQueryHandler(cb_menu_router, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(cb_brand_page, pattern=r"^brand:"))
    app.add_handler(CallbackQueryHandler(cb_detail, pattern=r"^detail:"))
    app.add_handler(CallbackQueryHandler(cb_alert_add, pattern=r"^alert_add:"))
    app.add_handler(CallbackQueryHandler(cb_alert_del, pattern=r"^alert_del:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^noop$"))

    # ── Scheduled job: check stock every 30 min
    app.job_queue.run_repeating(
        check_stock,
        interval=config.STOCK_CHECK_INTERVAL,
        first=60,  # first run 60s after start
    )

    logger.info("Bot starting — polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
