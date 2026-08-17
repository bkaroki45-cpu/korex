from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
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
    )