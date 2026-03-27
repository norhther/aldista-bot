"""Periodic job that checks stock and fires Telegram alerts."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

import catalog as cat
from handlers.alerts_handler import all_alerts, remove_alert

logger = logging.getLogger(__name__)


async def check_stock(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Stock check starting...")
    try:
        # Force fresh fetch from GitHub Pages
        cat.fetch_catalog(force=True)
    except Exception as exc:
        logger.error("Failed to refresh catalog: %s", exc)
        return

    state = all_alerts()
    if not state:
        return

    for user_id_str, product_ids in list(state.items()):
        user_id = int(user_id_str)
        for pid in list(product_ids):
            p = cat.get_by_id(pid)
            if p and p["stock_status"] == "in_stock":
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=(
                            f"🎉 *¡Volvió al stock!*\n\n"
                            f"*{p['name']}*\n"
                            f"💶 {p['price']}\n"
                            f"🔗 [Comprar ahora]({p['url']})"
                        ),
                        parse_mode="Markdown",
                        disable_web_page_preview=False,
                    )
                    remove_alert(user_id, pid)
                    logger.info("Notified user %s about product %s", user_id, pid)
                except Exception as exc:
                    logger.error("Could not notify user %s: %s", user_id, exc)
