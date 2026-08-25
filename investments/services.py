from datetime import datetime, time, timedelta
from decimal import Decimal
from random import SystemRandom
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from transactions.models import Transaction
from wallet.models import Wallet
from wallet.models import PlatformConfiguration
from memberships.models import Membership
from .models import EarningSession, Investment, Signal, SignalParticipation

KENYA_TZ = ZoneInfo("Africa/Nairobi")
SIGNAL_WINDOW = timedelta(minutes=15)
TRADE_SETTLEMENT_DELAY = timedelta(minutes=45)
SIGNAL_PROFIT_RATE = Decimal("0.0100")
SIGNAL_TIMES = ((Signal.Slot.MORNING, time(17, 0)), (Signal.Slot.AFTERNOON, time(19, 0)), (Signal.Slot.EVENING, time(20, 0)))
SIGNAL_TEMPLATES = (
    ("BTC/USDT", "BUY", Decimal("62000")), ("ETH/USDT", "BUY", Decimal("3200")),
    ("SOL/USDT", "SELL", Decimal("145")), ("XRP/USDT", "BUY", Decimal("0.55")),
    ("BNB/USDT", "SELL", Decimal("590")), ("DOGE/USDT", "BUY", Decimal("0.12")),
)
RANDOM = SystemRandom()


def kenya_today():
    return timezone.now().astimezone(KENYA_TZ).date()


def membership_for_user(user):
    """Return a membership for both new and legacy accounts."""
    membership, _ = Membership.objects.get_or_create(user=user)
    return membership


def create_scheduled_signals(for_date=None):
    """Idempotently create scheduled, simulated trade signals for Kenya time."""
    for_date = for_date or kenya_today()
    signals = []
    for slot, signal_time in SIGNAL_TIMES:
        pair, direction, baseline_entry = RANDOM.choice(SIGNAL_TEMPLATES)
        variation = Decimal(str(RANDOM.uniform(0.985, 1.015))).quantize(Decimal("0.00000001"))
        entry = (baseline_entry * variation).quantize(Decimal("0.00000001"))
        take_profit = (entry * (Decimal("1.012") if direction == "BUY" else Decimal("0.988"))).quantize(Decimal("0.00000001"))
        stop_loss = (entry * (Decimal("0.994") if direction == "BUY" else Decimal("1.006"))).quantize(Decimal("0.00000001"))
        signal, created = Signal.objects.get_or_create(
            signal_date=for_date, slot=slot,
            defaults={"scheduled_at": datetime.combine(for_date, signal_time, tzinfo=KENYA_TZ), "pair": pair,
                      "direction": direction, "entry_price": entry, "take_profit": take_profit,
                      "stop_loss": stop_loss, "profit_rate": SIGNAL_PROFIT_RATE, "status": Signal.Status.PUBLISHED},
        )
        # Populate legacy scheduled records that were created before signal details existed.
        if not created and signal.entry_price is None:
            signal.pair, signal.direction = pair, direction
            signal.entry_price, signal.take_profit, signal.stop_loss = entry, take_profit, stop_loss
            signal.profit_rate = SIGNAL_PROFIT_RATE
            signal.save(update_fields=["pair", "direction", "entry_price", "take_profit", "stop_loss", "profit_rate"])
        signals.append(signal)
    return signals


def eligible_signals_for_user(user, for_date=None):
    # Every user can see every published signal after it opens.  Eligibility is
    # intentionally enforced only when a user attempts to trade it.
    return Signal.objects.filter(
        signal_date=for_date or kenya_today(), status=Signal.Status.PUBLISHED,
        scheduled_at__lte=timezone.now(),
    ).order_by("scheduled_at")


@transaction.atomic
def mark_missed_signals(now=None):
    """Create immutable MISSED records after the 30-minute response window closes."""
    now = now or timezone.now()
    count = 0
    for signal in Signal.objects.filter(status=Signal.Status.PUBLISHED, scheduled_at__lte=now - SIGNAL_WINDOW):
        investments = Investment.objects.filter(status=Investment.Status.ACTIVE, start_date__lte=signal.scheduled_at, end_date__gt=signal.scheduled_at).select_related("user")
        for investment in investments:
            membership = membership_for_user(investment.user)
            if membership.membership_type == Membership.MembershipType.REGULAR and signal.slot == Signal.Slot.EVENING:
                continue
            _, created = EarningSession.objects.get_or_create(
                investment=investment, signal=signal,
                defaults={"user": investment.user, "session_date": signal.signal_date, "display_asset": signal.pair,
                          "display_direction": signal.direction, "display_entry_price": signal.entry_price,
                          "display_take_profit": signal.take_profit, "display_stop_loss": signal.stop_loss,
                          "earning_rate": signal.profit_rate, "status": EarningSession.Status.MISSED},
            )
            count += created
    return count


@transaction.atomic
def settle_due_trades(now=None):
    """Credit the wallet once, five hours after a simulated signal trade was recorded."""
    now = now or timezone.now()
    settled = 0
    for session in EarningSession.objects.select_for_update().filter(status=EarningSession.Status.ACTIVE, payout_due_at__lte=now).select_related("investment", "user", "signal"):
        wallet = Wallet.objects.select_for_update().get(user=session.user)
        amount = session.earning_amount
        before = wallet.available_balance
        wallet.available_balance += amount
        wallet.total_profit += amount
        wallet.save(update_fields=["available_balance", "total_profit", "updated_at"])
        session.status, session.settled_at = EarningSession.Status.SETTLED, now
        session.save(update_fields=["status", "settled_at"])
        investment = session.investment
        investment.total_profit += amount
        investment.current_value = investment.principal + investment.total_profit
        investment.save(update_fields=["total_profit", "current_value", "updated_at"])
        Transaction.objects.create(user=session.user, transaction_type=Transaction.TransactionType.PROFIT, amount=amount,
            balance_before=before, balance_after=wallet.available_balance, reference=f"SIGNAL-SETTLED-{session.id}",
            description=f"Settled simulated trade: {session.display_asset}", status=Transaction.Status.COMPLETED, completed_at=now)
        settled += 1
    return settled


@transaction.atomic
def mature_due_investments():
    now = timezone.now()
    matured = 0
    for investment in Investment.objects.select_for_update().filter(status=Investment.Status.ACTIVE, end_date__lte=now):
        wallet = Wallet.objects.select_for_update().get(user=investment.user)
        wallet.available_balance += investment.principal
        wallet.locked_balance -= investment.principal
        wallet.save(update_fields=["available_balance", "locked_balance", "updated_at"])
        investment.status = Investment.Status.COMPLETED
        investment.save(update_fields=["status", "updated_at"])
        matured += 1
    return matured


@transaction.atomic
def participate_in_signal(*, user, investment_id, signal_id):
    now = timezone.now()
    config = PlatformConfiguration.current()
    investment = Investment.objects.select_for_update().get(id=investment_id, user=user)
    signal = Signal.objects.select_for_update().get(id=signal_id)
    if investment.status != Investment.Status.ACTIVE or not investment.end_date or investment.end_date <= now:
        raise ValueError("This trade balance is not eligible for a signal.")
    if signal.status != Signal.Status.PUBLISHED or signal.scheduled_at > now:
        raise ValueError("This signal is not available yet.")
    if now > signal.scheduled_at + timedelta(minutes=config.signal_window_minutes):
        mark_missed_signals(now)
        raise ValueError("This signal expired after its 30-minute trade window.")
    membership = membership_for_user(user)
    if membership.membership_type == Membership.MembershipType.REGULAR and signal.slot == Signal.Slot.EVENING:
        raise ValueError("The 8:00 PM signal is available to Team Leaders only.")
    if SignalParticipation.objects.filter(user=user, investment=investment, signal=signal).exists():
        raise ValueError("This signal was already traded.")
    SignalParticipation.objects.create(user=user, investment=investment, signal=signal)
    # principal is the amount locked for this specific trade balance. A 1% signal
    # therefore pays 1% of that locked amount, not of the user's whole wallet.
    amount = (investment.principal * signal.profit_rate).quantize(Decimal("0.01"))
    session, created = EarningSession.objects.get_or_create(investment=investment, signal=signal, defaults={"user": user, "session_date": signal.signal_date})
    if not created or session.status == EarningSession.Status.MISSED:
        raise ValueError("This signal is marked missed.")
    session.display_asset, session.display_direction = signal.pair, signal.direction
    session.display_entry_price, session.display_take_profit, session.display_stop_loss = signal.entry_price, signal.take_profit, signal.stop_loss
    session.earning_rate, session.earning_amount = signal.profit_rate, amount
    session.status, session.participated_at, session.payout_due_at = EarningSession.Status.ACTIVE, now, now + timedelta(minutes=config.settlement_minutes)
    session.save()
    return amount, session.payout_due_at
