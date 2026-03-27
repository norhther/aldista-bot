"""Periodic job: detects restocked items and new catalog products, notifies users."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from telegram.ext import ContextTypes

import catalog as cat
import ui
import users
from handlers.alerts_handler import all_alerts, remove_alert

logger = logging.getLogger(__name__)

_KNOWN_IDS_FILE = Path(__file__).parent.parent / "known_ids.json"


def _load_known_ids() -> set[str]:
    if _KNOWN_IDS_FILE.exists():
        return set(json.loads(_KNOWN_IDS_FILE.read_text()))
    return set()


def _save_known_ids(ids: set[str]) -> None:
    _KNOWN_IDS_FILE.write_text(json.dumps(sorted(ids)))


async def check_stock(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Stock check running…")
    try:
        cat.fetch_catalog(force=True)
    except Exception as exc:
        logger.error("Catalog refresh failed: %s", exc)
        return

    products = cat.get_products()
    current_ids = {p["product_id"] for p in products}
    known_ids = _load_known_ids()

    # ── Detect genuinely new products ─────────────────────────────────────────
    if known_ids:
        new_product_ids = current_ids - known_ids
        if new_product_ids:
            new_products = sorted(
                [p for p in products if p["product_id"] in new_product_ids],
                key=lambda p: int(p["product_id"]),
                reverse=True,
            )
            logger.info("New catalog products detected: %s", new_product_ids)
            await _broadcast_new_products(context, new_products)

    _save_known_ids(current_ids)

    # ── Back-in-stock alerts ──────────────────────────────────────────────────
    alerts = all_alerts()
    for user_id_str, product_ids in list(alerts.items()):
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


async def _broadcast_new_products(
    context: ContextTypes.DEFAULT_TYPE, new_products: list[dict]
) -> None:
    registered = users.all_users()
    if not registered:
        return

    count = len(new_products)
    header = (
        f"✨ <b>{'1 nueva llegada al catálogo' if count == 1 else f'{count} nuevas llegadas al catálogo'}</b>\n"
        f"{ui.divider()}"
    )

    cards = "\n\n".join(
        f"{ui.product_card(p)}\n"
        f'🔗 <a href="{ui.e(p["url"])}">Ver en tienda →</a>'
        for p in new_products[:10]
    )

    footer = (
        f"\n{ui.divider()}\n<i>Usa /novedades para ver todo el catálogo nuevo.</i>"
        if count > 10
        else f"\n{ui.divider()}\n<i>Usa /novedades para ver todas las novedades.</i>"
    )

    text = f"{header}\n\n{cards}{footer}"

    for user_id in registered:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            logger.info("Broadcast new products to user %s", user_id)
        except Exception as exc:
            logger.error("Could not broadcast to user %s: %s", user_id, exc)
