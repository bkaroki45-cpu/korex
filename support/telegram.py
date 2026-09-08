"""Small, dependency-free Telegram alert client."""
import json
import logging
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def send_alert(text):
    """Send an admin alert without allowing Telegram downtime to break the website."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not token or not chat_id:
        return False
    payload = json.dumps({"chat_id": chat_id, "text": text[:4000]}).encode()
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5):
            return True
    except Exception:
        logger.exception("Telegram alert could not be sent")
        return False
