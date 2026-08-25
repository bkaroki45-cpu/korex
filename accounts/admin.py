from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email",
        "username",
        "phone_number",
        "account_id",
        "withdrawal_network",
        "is_verified",
        "is_staff",
        "created_at",
    )

    search_fields = (
        "email",
        "username",
        "phone_number",
        "referral_code",
    )

    ordering = ("-created_at",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "CLOUDD 1 Information",
            {
                "fields": (
                    "phone_number",
                    "account_id",
                    "withdrawal_address",
                    "withdrawal_network",
                    "referral_code",
                    "referred_by",
                    "is_verified",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "CLOUDD 1 Information",
            {
                "fields": (
                    "email",
                    "phone_number",
                    "withdrawal_address",
                    "withdrawal_network",
                    "referral_code",
                    "referred_by",
                    "is_verified",
                )
            },
        ),
    )
