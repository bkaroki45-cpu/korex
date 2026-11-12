from django.contrib import admin

from .models import SupportMessage, SupportRequest


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1
    fields = ("body", "is_staff_reply", "sender", "read_at", "created_at")
    readonly_fields = ("sender", "read_at", "created_at")

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                instance.sender = request.user
                instance.is_staff_reply = True
            instance.save()
        formset.save_m2m()


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "name", "email", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "subject", "message", "user__username", "user__account_id")
    readonly_fields = ("user", "name", "email", "subject", "message", "created_at", "updated_at")
    list_select_related = ("user",)
    inlines = (SupportMessageInline,)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                instance.sender = request.user
                instance.is_staff_reply = True
            instance.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()
