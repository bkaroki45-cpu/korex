from django.contrib import admin

from .models import Referral, ReferralProfile


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "referral_code",
        "total_referrals",
        "active_referrals",
        "team_volume",
        "referral_earnings",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__username",
    )


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):

    list_display = (
        "referrer",
        "referred_user",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "referrer__email",
        "referred_user__email",
    )
