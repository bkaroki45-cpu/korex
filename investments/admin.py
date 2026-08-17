from django.contrib import admin

from .models import Investment, EarningSession


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "principal",
        "current_value",
        "daily_rate",
        "total_profit",
        "status",
        "start_date",
    )

    list_filter = (
        "status",
        "start_date",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "start_date",
        "updated_at",
    )


@admin.register(EarningSession)
class EarningSessionAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "display_asset",
        "display_direction",
        "earning_rate",
        "earning_amount",
        "status",
        "session_date",
    )

    list_filter = (
        "status",
        "session_date",
        "display_asset",
    )

    search_fields = (
        "user__email",
        "user__username",
        "display_asset",
    )

    readonly_fields = (
        "created_at",
        "participated_at",
    )