from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.urls import reverse

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
    referral_link = request.build_absolute_uri(reverse("referrals:join", kwargs={"code": profile.referral_code}))
    return render(request, "referrals/overview.html", {"profile": profile, "team": team, "referral_link": referral_link})


def join_referral(request, code):
    """Validate a shared link before sending a visitor to registration."""
    normalized_code = code.strip().upper()
    if not ReferralProfile.objects.filter(referral_code=normalized_code).exists():
        return redirect("signup")
    return redirect(f"{reverse('signup')}?ref={normalized_code}")
