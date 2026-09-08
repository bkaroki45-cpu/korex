from django.contrib import admin

from .models import SupportRequest


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "name", "email", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "subject", "message", "user__username", "user__account_id")
    readonly_fields = ("user", "name", "email", "subject", "message", "created_at", "updated_at")
    list_select_related = ("user",)
