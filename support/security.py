"""Validation and abuse controls for public support requests."""
import hashlib
import hmac
import re

from django.conf import settings

SUSPICIOUS_INPUT = re.compile(
    r"(?:<\s*/?\s*script\b|<\s*(?:img|svg|iframe|object|embed|style)\b|"
    r"\{\{|\}\}|\{%|%\}|javascript\s*:|data\s*:\s*text/html|"
    r"(?:bxss|xss)\.me|on(?:error|load|click|focus)\s*=)",
    re.IGNORECASE,
)
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_support_text(value: str) -> str:
    """Normalize safe text and reject common injection/scanner payloads."""
    value = CONTROL_CHARACTERS.sub("", value or "")
    value = " ".join(value.split())
    if SUSPICIOUS_INPUT.search(value):
        raise ValueError("Please remove code, scripts, and links from your support request.")
    return value


def client_fingerprint(request) -> str:
    """Hash the proxied client address; never store the raw IP address."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    address = forwarded_for.split(",", 1)[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")
    return hmac.new(settings.SECRET_KEY.encode(), address.encode(), hashlib.sha256).hexdigest()