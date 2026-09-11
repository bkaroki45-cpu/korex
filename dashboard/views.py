from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from investments.models import Investment, Signal
from investments.services import create_scheduled_signals, kenya_today
from markets.services import get_market_news
from referrals.models import ReferralProfile
from referrals.services import new_referral_code
from transactions.models import Transaction
from wallet.models import PlatformConfiguration
from accounts.kyc import is_kyc_verified


@login_required
def dashboard(request):
    today = kenya_today()
    create_scheduled_signals(today)
    investments = Investment.objects.filter(user=request.user).order_by("-start_date")
    active_investment = investments.filter(status=Investment.Status.ACTIVE, end_date__gt=timezone.now()).first()
    referral_profile, _ = ReferralProfile.objects.get_or_create(
        user=request.user,
        defaults={"referral_code": new_referral_code()},
    )
    deposit_config = PlatformConfiguration.current()
    guides = [
        {"theme": "trader", "number": "01", "title": "CONNECT & CHOOSE A TRADER", "description": "Start in minutes and follow the best traders.", "steps": ["Create your account", "Browse top performing traders", "Choose who to copy"]},
        {"theme": "rewards", "number": "02", "title": "TRACK REWARDS & YOUR PROGRESS", "description": "Watch your signals, results and rewards in real time.", "steps": ["Live trade signals", "Real-time performance", "Earn rewards as you grow"]},
        {"theme": "referrals", "number": "03", "title": "INVITE & GROW YOUR NETWORK", "description": "Share your link and earn together with your team.", "steps": ["Get your referral link", "Invite friends and family", "Earn from their activity"]},
    ]
    return render(request, "dashboard/dashboard.html", {
        "wallet": request.user.wallet,
        # This is the same wallet field enforced by the withdrawal service.
        # It includes settled signal profits, referral rewards and released principal.
        "withdrawable_balance": request.user.wallet.available_balance,
        "active_investment": active_investment,
        "unlock_remaining_seconds": max(0, int((active_investment.end_date - timezone.now()).total_seconds())) if active_investment else 0,
        "signals": Signal.objects.filter(signal_date=today, status=Signal.Status.PUBLISHED, scheduled_at__lte=timezone.now()).order_by("scheduled_at"),
        "transactions": Transaction.objects.filter(user=request.user).order_by("-created_at")[:5],
        "completed_today": request.user.earning_sessions.filter(session_date=today, status="SETTLED").count(),
        "news": get_market_news() or [],
        "deposit_config": deposit_config,
        "guides": guides,
        "withdrawal_details_complete": bool(request.user.withdrawal_address and request.user.withdrawal_network),
        "kyc_verified": is_kyc_verified(request.user),
    })


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
