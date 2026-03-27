import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN: str = os.environ["TELEGRAM_TOKEN"]
ALDISTA_EMAIL: str = os.environ.get("ALDISTA_EMAIL", "")
ALDISTA_PASSWORD: str = os.environ.get("ALDISTA_PASSWORD", "")

CATALOG_URL = "https://norhther.github.io/aldista-catalog/catalog.json"
STOCK_CHECK_INTERVAL = 30 * 60  # 30 minutes in seconds
PAGE_SIZE = 8
