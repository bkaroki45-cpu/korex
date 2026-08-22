from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import timedelta

from .models import Investment, Signal, SignalParticipation
from .services import kenya_today, participate_in_signal

MINIMUM_INVESTMENT = Decimal("500.00")
PLAN_DETAILS = {name: {"name": name.title(), "minimum": MINIMUM_INVESTMENT, "daily_rate": Decimal("0.0200"), "duration_days": 35}
                for name in ("starter", "growth", "premium")}


@login_required
def investments(request):
    today = kenya_today()
    user_investments = Investment.objects.filter(user=request.user).order_by("-start_date")
    signals = Signal.objects.filter(signal_date=today, status=Signal.Status.PUBLISHED).order_by("scheduled_at")
    if request.user.membership.membership_type == request.user.membership.MembershipType.REGULAR:
        signals = signals.exclude(slot=Signal.Slot.AFTERNOON)
    active_investments = user_investments.filter(status=Investment.Status.ACTIVE, end_date__gt=timezone.now())
    participation_ids = set(SignalParticipation.objects.filter(user=request.user, signal__in=signals).values_list("signal_id", flat=True))
    paid_ids = set(user_investments.filter(earning_sessions__session_date=today, earning_sessions__status="PARTICIPATED").values_list("id", flat=True))
    return render(request, "investments/investments.html", {
        "investments": user_investments, "signals": signals, "active_investments": active_investments,
        "participation_ids": participation_ids, "paid_ids": paid_ids, "today": today,
    })


@login_required
def create_investment(request, plan):
    plan = plan.lower()
    if plan not in PLAN_DETAILS:
        messages.error(request, "Invalid investment plan.")
        return redirect("investments:investments")
    plan_details, wallet = PLAN_DETAILS[plan], request.user.wallet
    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount", "")).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Please enter a valid investment amount.")
            return redirect("investments:create_investment", plan=plan)
        if amount < MINIMUM_INVESTMENT:
            messages.error(request, "The minimum investment is $500.00.")
            return redirect("investments:create_investment", plan=plan)
        with transaction.atomic():
            wallet = type(wallet).objects.select_for_update().get(pk=wallet.pk)
            if amount > wallet.available_balance:
                messages.error(request, "Insufficient available wallet balance.")
                return redirect("investments:create_investment", plan=plan)
            wallet.available_balance -= amount
            wallet.locked_balance += amount
            wallet.save(update_fields=["available_balance", "locked_balance", "updated_at"])
            Investment.objects.create(user=request.user, principal=amount, current_value=amount,
                daily_rate=Decimal("0.0200"), duration_days=35,
                end_date=timezone.now() + timedelta(days=35), status=Investment.Status.ACTIVE)
            # A new active investment may qualify the referrer for Team Leader.
            try:
                referral = request.user.received_referral
            except Exception:
                referral = None
            if referral:
                from referrals.services import refresh_referrer_status
                refresh_referrer_status(referral.referrer)
        messages.success(request, f"Your ${amount} investment is active. Its principal is locked for 35 days.")
        return redirect("investments:investments")
    return render(request, "investments/create_investment.html", {"plan": plan, "plan_details": plan_details, "wallet": wallet})


@login_required
def participate(request, signal_id):
    if request.method != "POST":
        return redirect("investments:investments")
    investment_id = request.POST.get("investment_id")
    try:
        amount, paid = participate_in_signal(user=request.user, investment_id=int(investment_id), signal_id=signal_id)
    except Investment.DoesNotExist:
        messages.error(request, "Investment not found.")
    except Signal.DoesNotExist:
        messages.error(request, "Signal not found.")
    except (TypeError, ValueError) as error:
        messages.error(request, str(error) or "Choose a valid investment.")
    else:
        if paid:
            messages.success(request, f"Participation recorded. ${amount} profit was added to your available balance.")
        else:
            messages.success(request, "Participation recorded. This investment has already received its maximum 2% profit for today.")
    return redirect("investments:investments")


@login_required
def earning_sessions(request, investment_id):
    # Kept for existing links/bookmarks; the Investments page is now the signal entry point.
    get_object_or_404(Investment, id=investment_id, user=request.user)
    return redirect("investments:investments")
