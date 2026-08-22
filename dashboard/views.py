from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from investments.models import Investment, Signal
from investments.services import kenya_today
from transactions.models import Transaction


@login_required
def dashboard(request):
    today = kenya_today()
    investments = Investment.objects.filter(user=request.user).order_by("-start_date")
    return render(request, "dashboard/dashboard.html", {
        "wallet": request.user.wallet,
        "active_investment": investments.filter(status=Investment.Status.ACTIVE).first(),
        "signals": Signal.objects.filter(signal_date=today, status=Signal.Status.PUBLISHED).order_by("scheduled_at"),
        "transactions": Transaction.objects.filter(user=request.user).order_by("-created_at")[:5],
        "completed_today": request.user.earning_sessions.filter(session_date=today, status="SETTLED").count(),
    })


@login_required
def wallet_action(request, action):
    if request.method != "POST":
        return redirect("dashboard")
    if action == "deposit":
        messages.info(request, "Crypto deposits are not enabled yet. Your wallet is ready for that future integration.")
    elif action == "withdraw":
        messages.info(request, "Withdrawals will be available through the wallet withdrawal flow once it is enabled.")
    else:
        messages.error(request, "Unknown wallet action.")
    return redirect("dashboard")
