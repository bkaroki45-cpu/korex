"""Server-side helpers for Didit KYC state and webhook handling."""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone as datetime_timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DiditWebhookEvent, KYCVerification

logger = logging.getLogger(__name__)

DIDIT_SESSION_URL = "https://verification.didit.me/v3/session/"
STATUS_MAP = {
    "Not Started": KYCVerification.Status.NOT_STARTED,
    "In Progress": KYCVerification.Status.IN_PROGRESS,
    "Awaiting User": KYCVerification.Status.AWAITING_USER,
    "In Review": KYCVerification.Status.IN_REVIEW,
    "Approved": KYCVerification.Status.VERIFIED,
    "Declined": KYCVerification.Status.DECLINED,
    "Resubmitted": KYCVerification.Status.RESUBMITTED,
    "Abandoned": KYCVerification.Status.ABANDONED,
    "Expired": KYCVerification.Status.EXPIRED,
    "Kyc Expired": KYCVerification.Status.KYC_EXPIRED,
}


def is_kyc_verified(user):
    if not settings.KYC_ENFORCEMENT_ENABLED:
        return True
    return bool(user.is_authenticated and KYCVerification.objects.filter(
        user=user, status=KYCVerification.Status.VERIFIED
    ).exists())


def verification_for(user):
    return KYCVerification.objects.get_or_create(
        user=user, defaults={"vendor_data": str(user.pk)}
    )[0]


def create_didit_session(*, user, callback_url):
    if not settings.DIDIT_API_KEY:
        raise ValueError("Identity verification is temporarily unavailable. Please contact support.")
    payload = json.dumps({
        "workflow_id": settings.DIDIT_WORKFLOW_ID,
        "vendor_data": str(user.pk),
        "callback": callback_url,
        "callback_method": "both",
    }).encode("utf-8")
    request = Request(DIDIT_SESSION_URL, data=payload, method="POST", headers={
        "x-api-key": settings.DIDIT_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        logger.warning("Didit session creation failed with HTTP %s", error.code)
        raise ValueError("Identity verification could not be started. Please try again later.") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        logger.warning("Didit session creation failed: %s", type(error).__name__)
        raise ValueError("Identity verification could not be started. Please try again later.") from error
    if not data.get("session_id") or not data.get("url"):
        logger.warning("Didit returned an incomplete session response")
        raise ValueError("Identity verification could not be started. Please try again later.")
    verification = verification_for(user)
    status = STATUS_MAP.get(data.get("status"), KYCVerification.Status.NOT_STARTED)
    verification.didit_session_id = data["session_id"]
    verification.vendor_data = str(user.pk)
    verification.status = status
    verification.save(update_fields=["didit_session_id", "vendor_data", "status", "updated_at"])
    return {"url": data["url"], "session_id": data["session_id"]}


def _shorten_floats(value):
    if isinstance(value, dict):
        return {key: _shorten_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_shorten_floats(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonical_json(payload):
    return json.dumps(_shorten_floats(payload), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def verify_webhook_signature(payload, signature, timestamp):
    secret = settings.DIDIT_WEBHOOK_SECRET
    if not secret or not signature or not timestamp:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
        expected = hmac.new(secret.encode("utf-8"), canonical_json(payload).encode("utf-8"), hashlib.sha256).hexdigest()
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(expected, signature)


@transaction.atomic
def apply_webhook_event(payload):
    """Idempotently apply a signed Didit V3 session event."""
    event_id = payload.get("event_id")
    status = STATUS_MAP.get(payload.get("status"))
    session_id = payload.get("session_id", "")
    if not event_id or not status:
        return False
    try:
        DiditWebhookEvent.objects.create(event_id=event_id, webhook_type=payload.get("webhook_type", ""), session_id=session_id)
    except IntegrityError:
        return True
    verification = KYCVerification.objects.select_for_update().filter(didit_session_id=session_id).first()
    if verification is None:
        vendor_data = str(payload.get("vendor_data", ""))
        if vendor_data.isdigit():
            verification = KYCVerification.objects.select_for_update().filter(user_id=int(vendor_data)).first()
    if verification is None:
        logger.warning("Didit webhook %s could not be matched to a user", event_id)
        return False
    verification.status = status
    verification.didit_session_id = session_id or verification.didit_session_id
    verification.last_status_at = timezone.now()
    if status == KYCVerification.Status.VERIFIED:
        verification.verified_at = timezone.now()
    elif status == KYCVerification.Status.KYC_EXPIRED:
        verification.verified_at = None
    verification.save()
    verification.user.is_verified = status == KYCVerification.Status.VERIFIED
    verification.user.save(update_fields=["is_verified"])
    return True
