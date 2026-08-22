from decimal import Decimal
import secrets

from django.db import transaction

from investments.models import Investment
from memberships.models import Membership
from .models import Referral, ReferralProfile

TEAM_LEADER_MIN_ACTIVE_REFERRALS = 3


def new_referral_code():
    while True:
        code = secrets.token_urlsafe(6).upper()
        if not ReferralProfile.objects.filter(referral_code=code).exists():
            return code


@transaction.atomic
def refresh_referrer_status(referrer):
    profile, _ = ReferralProfile.objects.select_for_update().get_or_create(user=referrer, defaults={"referral_code": new_referral_code()})
    direct_users = Referral.objects.filter(referrer=referrer, is_active=True).values("referred_user")
    active_users = Investment.objects.filter(user_id__in=direct_users, status=Investment.Status.ACTIVE).values("user").distinct()
    profile.total_referrals = Referral.objects.filter(referrer=referrer).count()
    profile.active_referrals = active_users.count()
    profile.team_volume = sum((investment.principal for investment in Investment.objects.filter(user_id__in=active_users, status=Investment.Status.ACTIVE)), Decimal("0.00"))
    profile.save(update_fields=["total_referrals", "active_referrals", "team_volume", "updated_at"])
    membership, _ = Membership.objects.select_for_update().get_or_create(user=referrer)
    if profile.active_referrals >= TEAM_LEADER_MIN_ACTIVE_REFERRALS:
        membership.membership_type, membership.daily_sessions, membership.earning_rate = Membership.MembershipType.TEAM_LEADER, 3, Decimal("0.0300")
    else:
        membership.membership_type, membership.daily_sessions, membership.earning_rate = Membership.MembershipType.REGULAR, 2, Decimal("0.0200")
    membership.save(update_fields=["membership_type", "daily_sessions", "earning_rate", "updated_at"])
    return profile, membership


@transaction.atomic
def create_referral(*, referred_user, referral_code):
    profile = ReferralProfile.objects.select_for_update().filter(referral_code=referral_code.strip().upper()).select_related("user").first()
    if not profile:
        raise ValueError("That referral code is not valid.")
    if profile.user_id == referred_user.id:
        raise ValueError("You cannot use your own referral code.")
    referral, created = Referral.objects.get_or_create(referrer=profile.user, referred_user=referred_user)
    if not created:
        raise ValueError("This account already has a referral relationship.")
    refresh_referrer_status(profile.user)
    return referral
