
from django.contrib import admin

from .models import CryptoDeposit, DepositAddress, OnRampOrder, PlatformConfiguration, Wallet, WithdrawalNetwork, WithdrawalRequest
from .services import approve_manual_deposit, complete_withdrawal


@admin.register(DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "asset", "network", "address", "provider", "is_active", "created_at")
    list_filter = ("asset", "network", "provider", "is_active")
    search_fields = ("user__email", "address")
    readonly_fields = ("created_at",)


@admin.register(CryptoDeposit)
class CryptoDepositAdmin(admin.ModelAdmin):
    list_display = ("user", "account_id", "asset", "network", "amount", "transaction_hash", "status", "created_at", "approved_at")
    list_filter = ("asset", "network", "status")
    search_fields = ("user__email", "transaction_hash", "provider_reference", "deposit_address__address")
    readonly_fields = ("user", "deposit_address", "asset", "network", "amount", "transaction_hash", "provider_reference", "receiving_address", "proof", "credited_at", "confirmed_at", "approved_by", "approved_at", "created_at", "updated_at")
    actions = ("mark_completed", "reject_deposits")
    list_select_related = ("user", "approved_by")
    date_hierarchy = "created_at"
    @admin.display(description="CloudD 1 Account ID")
    def account_id(self, obj): return obj.user.account_id
    @admin.action(description="Mark selected pending deposits as completed")
    def mark_completed(self, request, queryset):
        for deposit in queryset:
            try: approve_manual_deposit(deposit_id=deposit.id, admin_user=request.user)
            except ValueError: pass
    @admin.action(description="Reject selected pending deposits")
    def reject_deposits(self, request, queryset): queryset.filter(status=CryptoDeposit.Status.PENDING).update(status=CryptoDeposit.Status.REJECTED)


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
    fields = ("user", "available_balance", "locked_balance", "total_profit", "total_deposited", "total_withdrawn", "updated_at")
    list_select_related = ("user",)

@admin.register(WithdrawalNetwork)
class WithdrawalNetworkAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_enabled")

@admin.register(PlatformConfiguration)
class PlatformConfigurationAdmin(admin.ModelAdmin):
    list_display = ("deposit_asset", "deposit_network", "minimum_deposit", "minimum_withdrawal", "principal_lock_days", "signal_window_minutes", "settlement_minutes", "team_leader_requirement")

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "account_id", "amount", "asset", "network", "status", "created_at", "completed_at")
    readonly_fields = ("user", "amount", "asset", "address", "network", "completed_by", "completed_at", "created_at")
    actions = ("mark_completed", "reject_requests")
    list_filter = ("status", "asset", "network", "created_at")
    search_fields = ("user__email", "user__account_id", "address")
    list_select_related = ("user", "completed_by")
    date_hierarchy = "created_at"
    @admin.display(description="CloudD 1 Account ID")
    def account_id(self, obj): return obj.user.account_id
    @admin.action(description="Mark selected pending withdrawals as completed")
    def mark_completed(self, request, queryset):
        for withdrawal in queryset:
            try: complete_withdrawal(withdrawal_id=withdrawal.id, admin_user=request.user)
            except ValueError: pass
    @admin.action(description="Reject selected pending withdrawals")
    def reject_requests(self, request, queryset):
        from django.db import transaction
        for withdrawal in queryset.filter(status=WithdrawalRequest.Status.PENDING):
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=withdrawal.user)
                wallet.available_balance += withdrawal.amount
                wallet.save(update_fields=["available_balance", "updated_at"])
                withdrawal.status = WithdrawalRequest.Status.REJECTED
                withdrawal.save(update_fields=["status"])
                from transactions.models import Transaction
                Transaction.objects.filter(reference=f"WITHDRAWAL-REQUEST-{withdrawal.id}").update(status=Transaction.Status.CANCELLED, description="Withdrawal request rejected; amount restored to wallet")
