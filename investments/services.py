from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from transactions.models import Transaction

from .models import EarningSession


@transaction.atomic
def participate_in_session(session):
    """
    Records a user's participation in an earning session.

    This is a platform earning session, not an executed
    cryptocurrency market trade.
    """

    if session.status != EarningSession.Status.AVAILABLE:
        raise ValueError("This session is no longer available.")

    investment = session.investment
    wallet = session.user.wallet

    if investment.status != investment.Status.ACTIVE:
        raise ValueError("The investment is not active.")

    amount = investment.current_value * session.earning_rate
    amount = amount.quantize(Decimal("0.01"))

    balance_before = wallet.available_balance

    wallet.available_balance += amount
    wallet.total_profit += amount
    wallet.save(
        update_fields=[
            "available_balance",
            "total_profit",
            "updated_at",
        ]
    )

    session.earning_amount = amount
    session.status = EarningSession.Status.PARTICIPATED
    session.participated_at = timezone.now()
    session.save(
        update_fields=[
            "earning_amount",
            "status",
            "participated_at",
        ]
    )

    Transaction.objects.create(
        user=session.user,
        transaction_type=Transaction.TransactionType.PROFIT,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.available_balance,
        reference=f"SESSION-{session.id}-{session.user.id}",
        description=(
            f"Earning session participation: "
            f"{session.display_asset}"
        ),
        status=Transaction.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    return amount