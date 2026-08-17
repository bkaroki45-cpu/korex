from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email",
        "username",
        "phone_number",
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
            "KOREX Information",
            {
                "fields": (
                    "phone_number",
                    "referral_code",
                    "referred_by",
                    "is_verified",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "KOREX Information",
            {
                "fields": (
                    "email",
                    "phone_number",
                    "referral_code",
                    "referred_by",
                    "is_verified",
                )
            },
        ),
    )