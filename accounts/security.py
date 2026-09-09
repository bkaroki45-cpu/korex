import hashlib
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import AuthenticationThrottle

LOCK_AFTER_FAILURES = 5
LOCK_DURATION = timedelta(minutes=10)


def _identifier(request, value):
    return hashlib.sha256(f"{request.META.get('REMOTE_ADDR', '')}|{str(value).strip().lower()}".encode()).hexdigest()


def is_locked(request, purpose, value):
    state = AuthenticationThrottle.objects.filter(identifier_hash=_identifier(request, value), purpose=purpose).first()
    return bool(state and state.locked_until and state.locked_until > timezone.now())


@transaction.atomic
def register_failure(request, purpose, value):
    state, _ = AuthenticationThrottle.objects.select_for_update().get_or_create(identifier_hash=_identifier(request, value), purpose=purpose)
    state.failures += 1
    if state.failures >= LOCK_AFTER_FAILURES:
        state.failures, state.locked_until = 0, timezone.now() + LOCK_DURATION
    state.save(update_fields=["failures", "locked_until", "updated_at"])


def clear_failures(request, purpose, value):
    AuthenticationThrottle.objects.filter(identifier_hash=_identifier(request, value), purpose=purpose).delete()
