from django import forms
from django.contrib import admin

from .models import Transaction
from .services import create_manual_locked_deposit


class ManualDepositForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("user", "amount", "description")
        help_texts = {"amount": "The amount is locked immediately and opens an active copy-trading balance."}


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    form = ManualDepositForm
    list_display = (
        "reference",
        "user",
        "transaction_type",
        "amount",
        "status",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "status",
        "created_at",
    )

    search_fields = (
        "reference",
        "user__email",
        "user__username",
    )

    readonly_fields = (
        "created_at",
        "completed_at",
    )
    autocomplete_fields = ("user",)
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    list_per_page = 25

    def get_fields(self, request, obj=None):
        if obj:
            return ("user", "transaction_type", "amount", "balance_before", "balance_after", "reference", "description", "status", "created_at", "completed_at")
        return ("user", "amount", "description")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "transaction_type", "amount", "balance_before", "balance_after", "reference", "description", "status", "created_at", "completed_at")
        return ()

    def save_model(self, request, obj, form, change):
        if change:
            return
        transaction = create_manual_locked_deposit(
            user=obj.user,
            amount=obj.amount,
            admin_user=request.user,
            description=obj.description,
        )
        obj.pk = transaction.pk

    def has_delete_permission(self, request, obj=None):
        return False
