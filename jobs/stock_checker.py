"""Periodic job: checks stock and sends Telegram alerts."""

from __future__ import annotations

import logging

from telegram.ext import ContextTypes

import catalog as cat
import ui
from handlers.alerts_handler import all_alerts, remove_alert

logger = logging.getLogger(__name__)


async def check_stock(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Stock check running…")
    try:
        cat.fetch_catalog(force=True)
    except Exception as exc:
        logger.error("Catalog refresh failed: %s", exc)
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
                            "🎉 <b>¡Volvió al stock!</b>\n"
                            f"{ui.divider()}\n"
                            f"{ui.product_card(p)}\n"
                            f"{ui.divider()}\n"
                            f'🛒 <a href="{ui.e(p["url"])}">Comprar ahora →</a>'
                        ),
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                    )
                    remove_alert(user_id, pid)
                    logger.info("Notified user %s — product %s back in stock", user_id, pid)
                except Exception as exc:
                    logger.error("Could not notify user %s: %s", user_id, exc)
