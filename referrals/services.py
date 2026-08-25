from decimal import Decimal
import secrets

from django.db import transaction

from investments.models import Investment
from memberships.models import Membership
from .models import Referral, ReferralProfile

TEAM_LEADER_MIN_ACTIVE_REFERRALS = 5


def new_referral_code():
    from accounts.models import User
    while True:
        code = secrets.token_urlsafe(6).upper()
        if not ReferralProfile.objects.filter(referral_code=code).exists() and not User.objects.filter(referral_code=code).exists():
            return code


@transaction.atomic
def refresh_referrer_status(referrer):
    profile, _ = ReferralProfile.objects.select_for_update().get_or_create(user=referrer, defaults={"referral_code": new_referral_code()})
    direct_users = Referral.objects.filter(referrer=referrer, is_active=True).values("referred_user")
    active_users = Investment.objects.filter(user_id__in=direct_users, status=Investment.Status.ACTIVE, deposit__status="COMPLETED").values("user").distinct()
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


def _reward_for(amount, recipient):
    tiers = ((Decimal("500"), Decimal("1000"), Decimal("20") if recipient == "user" else Decimal("40")),
        (Decimal("1000"), Decimal("2000"), Decimal("50") if recipient == "user" else Decimal("70")),
        (Decimal("2000"), Decimal("3000"), Decimal("100") if recipient == "user" else Decimal("150")),
        (Decimal("3000"), Decimal("5000"), Decimal("180") if recipient == "user" else Decimal("270")))
    for low, high, reward in tiers:
        if low <= amount < high:
            return reward
    if amount >= Decimal("10000"):
        return (amount * (Decimal("0.06") if recipient == "user" else Decimal("0.12"))).quantize(Decimal("0.01"))
    if amount >= Decimal("5000"):
        return (amount * (Decimal("0.04") if recipient == "user" else Decimal("0.08"))).quantize(Decimal("0.01"))
    return Decimal("0.00")


@transaction.atomic
def grant_deposit_rewards(*, deposit):
    """Idempotent referral credits, only after a qualifying manual approval."""
    from transactions.models import Transaction
    from wallet.models import Wallet
    try:
        referral = Referral.objects.select_related("referrer", "referred_user").get(referred_user=deposit.user, is_active=True)
    except Referral.DoesNotExist:
        return
    for recipient, kind in ((referral.referred_user, "user"), (referral.referrer, "referrer")):
        reference = f"REFERRAL-DEPOSIT-{deposit.id}-{kind}"
        if Transaction.objects.filter(reference=reference).exists():
            continue
        reward = _reward_for(deposit.amount, kind)
        wallet = Wallet.objects.select_for_update().get(user=recipient)
        before = wallet.available_balance
        wallet.available_balance += reward
        wallet.save(update_fields=["available_balance", "updated_at"])
        if kind == "referrer":
            profile, _ = ReferralProfile.objects.select_for_update().get_or_create(user=recipient, defaults={"referral_code": new_referral_code()})
            profile.referral_earnings += reward
            profile.save(update_fields=["referral_earnings", "updated_at"])
        Transaction.objects.create(user=recipient, transaction_type=Transaction.TransactionType.REFERRAL, amount=reward,
            balance_before=before, balance_after=wallet.available_balance, reference=reference,
            description=f"Referral reward for approved deposit {deposit.id}", status=Transaction.Status.COMPLETED)
