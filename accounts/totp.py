"""RFC 6238 TOTP and encrypted account-secret helpers."""
import base64
import hashlib
import hmac
import secrets
import struct
import time

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from .models import RecoveryCode

TOTP_PERIOD = 30
TOTP_DIGITS = 6
RECOVERY_CODE_COUNT = 10


def _fernet():
    configured_key = settings.TWO_FACTOR_ENCRYPTION_KEY
    if configured_key:
        return Fernet(configured_key.encode())
    key = base64.urlsafe_b64encode(hashlib.sha256(f"{settings.SECRET_KEY}:totp".encode()).digest())
    return Fernet(key)


def generate_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def encrypt_secret(secret):
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret):
    return _fernet().decrypt(encrypted_secret.encode()).decode()


def _code(secret, counter):
    padded = secret + "=" * (-len(secret) % 8)
    digest = hmac.new(base64.b32decode(padded, casefold=True), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp(secret, code, timestamp=None, valid_window=1):
    code = "".join(str(code).split())
    if not (code.isdigit() and len(code) == TOTP_DIGITS):
        return False
    counter = int((timestamp or time.time()) // TOTP_PERIOD)
    return any(hmac.compare_digest(_code(secret, counter + offset), code) for offset in range(-valid_window, valid_window + 1))


def generate_recovery_codes(two_factor):
    two_factor.recovery_codes.all().delete()
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = [f"{''.join(secrets.choice(alphabet) for _ in range(4))}-{''.join(secrets.choice(alphabet) for _ in range(4))}" for _ in range(RECOVERY_CODE_COUNT)]
    RecoveryCode.objects.bulk_create([RecoveryCode(two_factor=two_factor, lookup_digest=_recovery_digest(code), code_hash=make_password(code)) for code in codes])
    return codes


def use_recovery_code(two_factor, code):
    normalized = code.strip().upper().replace(" ", "")
    recovery_code = two_factor.recovery_codes.filter(used_at__isnull=True, lookup_digest=_recovery_digest(normalized)).first()
    if not recovery_code or not check_password(normalized, recovery_code.code_hash):
        return False
    recovery_code.used_at = timezone.now()
    recovery_code.save(update_fields=["used_at"])
    return True


def _recovery_digest(code):
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()
