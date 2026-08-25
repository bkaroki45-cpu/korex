import secrets
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from investments.models import Investment
from wallet.models import PlatformConfiguration, Wallet

from .models import Transaction


@transaction.atomic
def create_manual_locked_deposit(*, user, amount, admin_user, description=""):
    """Record an admin-verified deposit and make it available for copy signals."""
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    config = PlatformConfiguration.current()
    if amount < config.minimum_deposit:
        raise ValueError(f"Manual deposits must be at least ${config.minimum_deposit:.2f}.")

    wallet = Wallet.objects.select_for_update().get(user=user)
    before = wallet.locked_balance
    wallet.locked_balance += amount
    wallet.total_deposited += amount
    wallet.save(update_fields=["locked_balance", "total_deposited", "updated_at"])

    now = timezone.now()
    Investment.objects.create(
        user=user,
        principal=amount,
        current_value=amount,
        daily_rate=Decimal("0.0100"),
        duration_days=config.principal_lock_days,
        end_date=now + timedelta(days=config.principal_lock_days),
        status=Investment.Status.ACTIVE,
    )
    reference = f"ADMIN-DEPOSIT-{secrets.token_urlsafe(10).upper()}"
    return Transaction.objects.create(
        user=user,
        transaction_type=Transaction.TransactionType.DEPOSIT,
        amount=amount,
        balance_before=before,
        balance_after=wallet.locked_balance,
        reference=reference,
        description=description or f"Manual deposit verified by {admin_user.get_username()}; principal locked for copy signals.",
        status=Transaction.Status.COMPLETED,
        completed_at=now,
    )
