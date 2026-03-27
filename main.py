"""Aldista Tobacco Telegram Bot — entry point."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
)

import config
from handlers.start import start, help_cmd, cb_main_menu
from handlers.list_handler import (
    list_cmd,
    brands_cmd,
    stats_cmd,
    novedades_cmd,
    cb_list_page,
    cb_novedades_page,
    cb_brand_page,
    cb_brands,
    cb_stats,
    cb_detail,
)
from handlers.search_handler import build_search_conversation
from handlers.alerts_handler import (
    myalerts_cmd,
    cb_alert_add,
    cb_alert_del,
    cb_alerts_menu,
    build_alert_conversation,
)
from jobs.stock_checker import check_stock

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cb_menu_search(update, context) -> None:
    """Prompt user to type a search query via callback."""
    import ui
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 <b>Buscar tabaco</b>\n"
        f"{ui.divider()}\n"
        "Envía el nombre, marca o referencia que buscas.\n"
        "<i>Cancela con /cancel</i>",
        parse_mode="HTML",
    )


def main() -> None:
    app: Application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # ── Conversations first (higher priority)
    app.add_handler(build_search_conversation())
    app.add_handler(build_alert_conversation())

    # ── Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("brands", brands_cmd))
    app.add_handler(CommandHandler("novedades", novedades_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("myalerts", myalerts_cmd))

    # ── Menu callbacks (pattern: menu:<action>[:<page>])
    app.add_handler(CallbackQueryHandler(cb_main_menu,      pattern=r"^menu:main$"))
    app.add_handler(CallbackQueryHandler(cb_list_page,      pattern=r"^menu:list:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_novedades_page, pattern=r"^menu:novedades:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_brands,         pattern=r"^menu:brands$"))
    app.add_handler(CallbackQueryHandler(cb_stats,          pattern=r"^menu:stats$"))
    app.add_handler(CallbackQueryHandler(cb_alerts_menu,    pattern=r"^menu:alerts$"))
    app.add_handler(CallbackQueryHandler(cb_menu_search,    pattern=r"^menu:search$"))

    # ── Catalog callbacks
    app.add_handler(CallbackQueryHandler(cb_brand_page, pattern=r"^brand:.+:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_detail,     pattern=r"^detail:"))

    # ── Alert callbacks
    app.add_handler(CallbackQueryHandler(cb_alert_add, pattern=r"^alert_add:"))
    app.add_handler(CallbackQueryHandler(cb_alert_del, pattern=r"^alert_del:"))

    # ── Scheduled stock check
    app.job_queue.run_repeating(
        check_stock,
        interval=config.STOCK_CHECK_INTERVAL,
        first=60,
    )

    logger.info("Bot starting — polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
