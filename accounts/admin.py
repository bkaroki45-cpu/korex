from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DiditWebhookEvent, KYCVerification, User


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


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "didit_session_id", "verified_at", "last_status_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__username", "didit_session_id", "vendor_data")
    readonly_fields = ("created_at", "updated_at", "verified_at", "last_status_at")
    list_select_related = ("user",)


@admin.register(DiditWebhookEvent)
class DiditWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "webhook_type", "session_id", "processed_at")
    search_fields = ("event_id", "session_id")
    readonly_fields = ("event_id", "webhook_type", "session_id", "processed_at")
