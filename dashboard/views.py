from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from decimal import Decimal

from investments.models import Investment, Signal
from investments.services import create_scheduled_signals, kenya_today
from markets.services import get_market_news
from referrals.models import ReferralProfile
from referrals.services import new_referral_code
from transactions.models import Transaction
from wallet.models import PlatformConfiguration


@login_required
def dashboard(request):
    today = kenya_today()
    create_scheduled_signals(today)
    investments = Investment.objects.filter(user=request.user).order_by("-start_date")
    referral_profile, _ = ReferralProfile.objects.get_or_create(
        user=request.user,
        defaults={"referral_code": new_referral_code()},
    )
    return render(request, "dashboard/dashboard.html", {
        "wallet": request.user.wallet,
        "withdrawable_balance": wallet_withdrawable(request.user.wallet, referral_profile),
        "active_investment": investments.filter(status=Investment.Status.ACTIVE).first(),
        "signals": Signal.objects.filter(signal_date=today, status=Signal.Status.PUBLISHED, scheduled_at__lte=timezone.now()).order_by("scheduled_at"),
        "transactions": Transaction.objects.filter(user=request.user).order_by("-created_at")[:5],
        "completed_today": request.user.earning_sessions.filter(session_date=today, status="SETTLED").count(),
        "news": get_market_news() or [],
        "deposit_config": PlatformConfiguration.current(),
        "withdrawal_details_complete": bool(request.user.withdrawal_address and request.user.withdrawal_network),
    })


def wallet_withdrawable(wallet, referral_profile):
    return wallet.total_profit + (referral_profile.referral_earnings or Decimal("0.00"))


@login_required
def wallet_action(request, action):
    if request.method != "POST":
        return redirect("dashboard")
    if action == "deposit":
        return redirect("dashboard")
    elif action == "withdraw":
        messages.info(request, "Withdrawals will be available through the wallet withdrawal flow once it is enabled.")
    else:
        messages.error(request, "Unknown wallet action.")
    return redirect("dashboard")
