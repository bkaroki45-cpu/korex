"""Brevo email verification and cryptographic trusted-device helpers."""
import hashlib
import secrets
from smtplib import SMTPException
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailVerificationCode, TrustedDevice

CODE_LIFETIME = timedelta(minutes=10)
DEVICE_LIFETIME = timedelta(days=30)
TRUSTED_DEVICE_COOKIE = "cloudd1_trusted_device"


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_code(user, purpose=EmailVerificationCode.Purpose.LOGIN):
    """Invalidate prior codes and send a freshly generated code. Never log it."""
    if not settings.DEBUG and (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD or not settings.DEFAULT_FROM_EMAIL):
        raise RuntimeError("Email verification is not configured. Please contact support.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        EmailVerificationCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        EmailVerificationCode.objects.create(user=user, purpose=purpose, code_hash=make_password(code), expires_at=timezone.now() + CODE_LIFETIME)
    name = user.get_full_name() or user.first_name or "there"
    is_reset = purpose == EmailVerificationCode.Purpose.PASSWORD_RESET
    try:
        send_mail(
            "Your CloudD 1 password reset code" if is_reset else "Your CloudD 1 verification code",
            f"Hello {name},\n\nYour CloudD 1 {'password reset' if is_reset else 'verification'} code is:\n\n{code}\n\nThis code expires in 10 minutes.\n\nIf you did not request this, you can safely ignore this email.\n\nDo not share this code with anyone.\n\nRegards,\nCloudD 1",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except SMTPException as error:
        EmailVerificationCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=timezone.now())
        raise RuntimeError("We could not send a verification email right now. Please try again later.") from error


@transaction.atomic
def verify_code(user, code, purpose=EmailVerificationCode.Purpose.LOGIN):
    verification = EmailVerificationCode.objects.select_for_update().filter(user=user, purpose=purpose, used_at__isnull=True).order_by("-created_at").first()
    if not verification or verification.expires_at <= timezone.now() or verification.attempts >= 5:
        return False
    if not check_password(code, verification.code_hash):
        verification.attempts += 1
        verification.save(update_fields=["attempts"])
        return False
    verification.used_at = timezone.now()
    verification.save(update_fields=["used_at"])
    if purpose == EmailVerificationCode.Purpose.LOGIN and not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
    return True


def create_trusted_device(user, request):
    token = secrets.token_urlsafe(48)
    label = request.META.get("HTTP_USER_AGENT", "Browser")[:180]
    device = TrustedDevice.objects.create(user=user, token_hash=_token_hash(token), label=label, expires_at=timezone.now() + DEVICE_LIFETIME)
    return device, token


def trusted_device_for_request(user, request):
    token = request.COOKIES.get(TRUSTED_DEVICE_COOKIE)
    if not token:
        return None
    device = TrustedDevice.objects.filter(user=user, token_hash=_token_hash(token), revoked_at__isnull=True, expires_at__gt=timezone.now()).first()
    if device:
        device.save(update_fields=["last_used_at"])
    return device


def set_trusted_device_cookie(response, token):
    response.set_cookie(TRUSTED_DEVICE_COOKIE, token, max_age=int(DEVICE_LIFETIME.total_seconds()), httponly=True, secure=not settings.DEBUG, samesite="Lax")


def clear_trusted_device_cookie(response):
    response.delete_cookie(TRUSTED_DEVICE_COOKIE, samesite="Lax")
