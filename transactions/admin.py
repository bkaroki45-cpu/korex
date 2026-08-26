from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path

from .models import Transaction
from .services import create_manual_locked_deposit
from wallet.models import WithdrawalRequest
from wallet.services import complete_withdrawal


class ManualDepositForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ("user", "amount", "description")
        help_texts = {"amount": "The amount is locked immediately and opens an active copy-trading balance."}


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    form = ManualDepositForm
    change_form_template = "admin/transactions/transaction/change_form.html"
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:transaction_id>/complete-withdrawal/",
                self.admin_site.admin_view(self.complete_withdrawal_view),
                name="transactions_transaction_complete_withdrawal",
            ),
        ]
        return custom_urls + urls

    def complete_withdrawal_view(self, request, transaction_id):
        ledger_entry = get_object_or_404(Transaction, pk=transaction_id)
        if request.method != "POST":
            return redirect("admin:transactions_transaction_change", transaction_id)

        prefix = "WITHDRAWAL-REQUEST-"
        if (
            ledger_entry.transaction_type != Transaction.TransactionType.WITHDRAWAL
            or not ledger_entry.reference.startswith(prefix)
            or not ledger_entry.reference[len(prefix):].isdigit()
        ):
            self.message_user(request, "This is not a withdrawal transaction linked to a withdrawal request.", level=messages.ERROR)
            return redirect("admin:transactions_transaction_change", transaction_id)

        withdrawal = get_object_or_404(
            WithdrawalRequest,
            pk=int(ledger_entry.reference[len(prefix):]),
            user=ledger_entry.user,
        )
        try:
            complete_withdrawal(withdrawal_id=withdrawal.id, admin_user=request.user)
        except ValueError as error:
            self.message_user(request, str(error), level=messages.ERROR)
        else:
            self.message_user(request, "Withdrawal and the user's transaction were marked Completed.", level=messages.SUCCESS)
        return redirect("admin:transactions_transaction_change", transaction_id)

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
