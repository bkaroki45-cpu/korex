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
    list_filter = ("is_staff", "is_verified", "withdrawal_network", "country", "is_active")
    list_select_related = ("referred_by",)
    readonly_fields = ("account_id", "created_at", "last_login", "date_joined")
    date_hierarchy = "created_at"
    list_per_page = 25
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        ("Account", {"fields": ("email", "username", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "phone_number", "country")}),
        ("CLOUDD 1 account", {"fields": ("account_id", "withdrawal_address", "withdrawal_network", "referral_code", "referred_by", "is_verified")}),
        ("Access and permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at")}),
    )

    add_fieldsets = (
        (
            "New account",
            {
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "country",
                    "withdrawal_address",
                    "withdrawal_network",
                    "referral_code",
                    "referred_by",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                )
            },
        ),
    )
