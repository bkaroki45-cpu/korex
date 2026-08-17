from django.conf import settings
from django.db import models


class ReferralProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_profile",
    )

    total_referrals = models.PositiveIntegerField(
        default=0,
    )

    active_referrals = models.PositiveIntegerField(
        default=0,
    )

    team_volume = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    referral_earnings = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.email} Referral Profile"


class Referral(models.Model):

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_referrals",
    )

    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_referral",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return (
            f"{self.referrer.email} → "
            f"{self.referred_user.email}"
        )