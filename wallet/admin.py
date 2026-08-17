
from django.contrib import admin

from .models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "available_balance",
        "locked_balance",
        "total_profit",
        "total_deposited",
        "total_withdrawn",
        "updated_at",
    )

    search_fields = (
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "updated_at",
    )