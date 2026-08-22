from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from investments.models import Investment
from .models import Referral, ReferralProfile
from .services import new_referral_code


@login_required
def referrals_earnings(request):
    profile, _ = ReferralProfile.objects.get_or_create(
        user=request.user,
        defaults={"referral_code": new_referral_code()},
    )
    referrals = Referral.objects.filter(referrer=request.user).select_related("referred_user").order_by("-created_at")
    team = []
    for referral in referrals:
        user = referral.referred_user
        active = user.investments.filter(status=Investment.Status.ACTIVE).exists()
        team.append({"user": user, "joined": referral.created_at, "active": active,
                     "trade_profit": user.investments.aggregate(total=Sum("total_profit"))["total"] or 0})
    referral_link = request.build_absolute_uri(f"/accounts/signup/?ref={profile.referral_code}")
    return render(request, "referrals/overview.html", {"profile": profile, "team": team, "referral_link": referral_link})
