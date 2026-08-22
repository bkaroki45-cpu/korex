from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from transactions.models import Transaction
from wallet.models import Wallet
from .models import EarningSession, Investment, Signal, SignalParticipation

KENYA_TZ = ZoneInfo("Africa/Nairobi")
SIGNAL_TIMES = ((Signal.Slot.MORNING, time(10, 0)), (Signal.Slot.AFTERNOON, time(15, 0)), (Signal.Slot.EVENING, time(21, 0)))


def kenya_today():
    return timezone.now().astimezone(KENYA_TZ).date()


def create_scheduled_signals(for_date=None):
    """Idempotent scheduler entry point; call it from Celery Beat, cron, or a command."""
    for_date = for_date or kenya_today()
    signals = []
    for slot, signal_time in SIGNAL_TIMES:
        scheduled_at = datetime.combine(for_date, signal_time, tzinfo=KENYA_TZ)
        signal, _ = Signal.objects.get_or_create(
            signal_date=for_date, slot=slot,
            defaults={"scheduled_at": scheduled_at, "status": Signal.Status.PUBLISHED},
        )
        signals.append(signal)
    return signals


@transaction.atomic
def mature_due_investments():
    """Return due locked principal exactly once. Safe to run repeatedly."""
    now = timezone.now()
    matured = 0
    for investment in Investment.objects.select_for_update().filter(status=Investment.Status.ACTIVE, end_date__lte=now):
        wallet = Wallet.objects.select_for_update().get(user=investment.user)
        wallet.available_balance += investment.principal
        wallet.locked_balance -= investment.principal
        wallet.save(update_fields=["available_balance", "locked_balance", "updated_at"])
        investment.status = Investment.Status.COMPLETED
        investment.save(update_fields=["status", "updated_at"])
        try:
            referral = investment.user.received_referral
        except Exception:
            referral = None
        if referral:
            from referrals.services import refresh_referrer_status
            refresh_referrer_status(referral.referrer)
        matured += 1
    return matured


@transaction.atomic
def participate_in_signal(*, user, investment_id, signal_id):
    today = kenya_today()
    investment = Investment.objects.select_for_update().get(id=investment_id, user=user)
    signal = Signal.objects.select_for_update().get(id=signal_id)
    now = timezone.now()
    if investment.status != Investment.Status.ACTIVE or not investment.end_date or investment.end_date <= now:
        raise ValueError("This investment is not eligible for a signal.")
    if signal.status != Signal.Status.PUBLISHED or signal.signal_date != today or signal.scheduled_at > now:
        raise ValueError("This signal is not currently available.")
    membership = user.membership
    if membership.membership_type == membership.MembershipType.REGULAR and signal.slot == Signal.Slot.AFTERNOON:
        raise ValueError("The third daily signal is available to Team Leaders only.")
    if SignalParticipation.objects.filter(user=user, investment=investment, signal=signal).exists():
        raise ValueError("You have already participated in this signal.")
    SignalParticipation.objects.create(user=user, investment=investment, signal=signal)
    try:
        session = EarningSession.objects.select_for_update().get(investment=investment, signal=signal)
    except EarningSession.DoesNotExist:
        session = None
    if session and session.status == EarningSession.Status.PARTICIPATED:
        return Decimal("0.00"), False
    earning_rate = Decimal(membership.earning_rate)
    amount = (investment.principal * earning_rate).quantize(Decimal("0.01"))
    wallet = Wallet.objects.select_for_update().get(user=user)
    balance_before = wallet.available_balance
    wallet.available_balance += amount
    wallet.total_profit += amount
    wallet.save(update_fields=["available_balance", "total_profit", "updated_at"])
    if session is None:
        session = EarningSession(investment=investment, user=user, signal=signal, session_date=today)
    session.display_asset, session.display_direction = signal.pair, signal.direction
    session.display_entry_price, session.display_take_profit, session.display_stop_loss = signal.entry_price, signal.take_profit, signal.stop_loss
    session.earning_rate, session.earning_amount = earning_rate, amount
    session.status, session.participated_at = EarningSession.Status.PARTICIPATED, now
    session.save()
    Transaction.objects.create(user=user, transaction_type=Transaction.TransactionType.PROFIT, amount=amount,
        balance_before=balance_before, balance_after=wallet.available_balance,
        reference=f"SIGNAL-PROFIT-{investment.id}-{signal.id}",
        description=f"Daily signal profit for investment #{investment.id}", status=Transaction.Status.COMPLETED, completed_at=now)
    investment.total_profit += amount
    investment.current_value = investment.principal + investment.total_profit
    investment.save(update_fields=["total_profit", "current_value", "updated_at"])
    return amount, True
