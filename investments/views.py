from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.utils.timezone import timedelta

from .models import Investment, EarningSession


PLAN_DETAILS = {
    "starter": {
        "name": "Starter",
        "minimum": Decimal("10.00"),
        "daily_rate": Decimal("0.0200"),
        "duration_days": 30,
    },
    "growth": {
        "name": "Growth",
        "minimum": Decimal("50.00"),
        "daily_rate": Decimal("0.0300"),
        "duration_days": 30,
    },
    "premium": {
        "name": "Premium",
        "minimum": Decimal("100.00"),
        "daily_rate": Decimal("0.0400"),
        "duration_days": 30,
    },
}


@login_required
def investments(request):

    user_investments = Investment.objects.filter(
        user=request.user
    ).order_by("-start_date")

    return render(
        request,
        "investments/investments.html",
        {
            "investments": user_investments,
        }
    )


@login_required
def create_investment(request, plan):

    plan = plan.lower()

    if plan not in PLAN_DETAILS:
        messages.error(
            request,
            "Invalid investment plan."
        )
        return redirect("investments")

    plan_details = PLAN_DETAILS[plan]

    wallet = request.user.wallet

    if request.method == "POST":

        amount = request.POST.get("amount")

        try:
            amount = Decimal(amount)
        except (TypeError, ValueError):
            messages.error(
                request,
                "Please enter a valid investment amount."
            )

            return redirect(
                "create_investment",
                plan=plan
            )

        # Keep amount to 2 decimal places
        amount = amount.quantize(
            Decimal("0.01")
        )

        # Check minimum investment
        if amount < plan_details["minimum"]:

            messages.error(
                request,
                f"The minimum investment for "
                f"{plan_details['name']} is "
                f"${plan_details['minimum']}."
            )

            return redirect(
                "create_investment",
                plan=plan
            )

        # Check wallet balance
        if amount > wallet.available_balance:

            messages.error(
                request,
                "Insufficient available wallet balance."
            )

            return redirect(
                "create_investment",
                plan=plan
            )

        with transaction.atomic():

            # --------------------------------
            # MOVE MONEY INTO LOCKED BALANCE
            # --------------------------------

            wallet.available_balance -= amount
            wallet.locked_balance += amount

            wallet.save(
                update_fields=[
                    "available_balance",
                    "locked_balance",
                    "updated_at",
                ]
            )

            # --------------------------------
            # CREATE INVESTMENT
            # --------------------------------

            investment = Investment.objects.create(

                user=request.user,

                principal=amount,

                current_value=amount,

                daily_rate=plan_details["daily_rate"],

                duration_days=plan_details["duration_days"],

                end_date=(
                    timezone.now()
                    + timedelta(
                        days=plan_details["duration_days"]
                    )
                ),

                status=Investment.Status.ACTIVE,

                total_profit=Decimal("0.00"),
            )

            # --------------------------------
            # CALCULATE DAILY EARNING
            # --------------------------------

            daily_profit = (
                amount
                * plan_details["daily_rate"]
            ).quantize(
                Decimal("0.01")
            )

            # --------------------------------
            # CREATE TODAY'S EARNING SESSION
            # --------------------------------

            EarningSession.objects.create(

                investment=investment,

                user=request.user,

                session_date=timezone.localdate(),

                display_asset="BTC/USDT",

                display_direction="BUY",

                earning_rate=plan_details[
                    "daily_rate"
                ],

                earning_amount=daily_profit,

                status=EarningSession.Status.AVAILABLE,
            )

        # --------------------------------
        # SUCCESS MESSAGE
        # --------------------------------

        messages.success(
            request,
            f"Your ${amount} "
            f"{plan_details['name']} investment "
            "was created successfully."
        )

        return redirect("investments")

    # --------------------------------
    # CREATE INVESTMENT PAGE
    # --------------------------------

    return render(
        request,
        "investments/create_investment.html",
        {
            "plan": plan,
            "plan_details": plan_details,
            "wallet": wallet,
        }
    )


@login_required
def earning_sessions(request, investment_id):

    investment = get_object_or_404(
        Investment,
        id=investment_id,
        user=request.user,
    )

    sessions = investment.earning_sessions.filter(
        session_date=timezone.localdate()
    ).order_by("created_at")

    return render(
        request,
        "investments/earning_sessions.html",
        {
            "investment": investment,
            "sessions": sessions,
        }
    )