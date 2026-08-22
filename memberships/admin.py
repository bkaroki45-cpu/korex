from django.contrib import admin

from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "membership_type",
        "daily_sessions",
        "earning_rate",
        "is_active",
        "activated_at",
        "updated_at",
    )

    list_filter = (
        "membership_type",
        "is_active",
    )

    search_fields = (
        "user__email",
        "user__username",
    )
