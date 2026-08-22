
from django.contrib import admin

from .models import CryptoDeposit, DepositAddress, OnRampOrder, Wallet


@admin.register(DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "network", "address", "provider", "is_active", "created_at")
    list_filter = ("asset", "network", "provider", "is_active")
    search_fields = ("user__email", "address")
    readonly_fields = ("created_at",)


@admin.register(CryptoDeposit)
class CryptoDepositAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "network", "amount", "transaction_hash", "status", "created_at", "confirmed_at", "credited_at")
    list_filter = ("asset", "network", "status")
    search_fields = ("user__email", "transaction_hash", "provider_reference", "deposit_address__address")
    readonly_fields = ("user", "deposit_address", "asset", "network", "amount", "transaction_hash", "provider_reference", "credited_at", "confirmed_at", "created_at", "updated_at")


@admin.register(OnRampOrder)
class OnRampOrderAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "amount_kes", "estimated_usdt", "status", "provider_reference", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("user__email", "provider_reference")
    readonly_fields = ("created_at", "updated_at")

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
