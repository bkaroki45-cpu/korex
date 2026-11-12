from .models import SupportMessage


def support_notifications(request):
    if not request.user.is_authenticated:
        return {"support_unread_count": 0, "support_notifications": []}
    notifications = SupportMessage.objects.filter(
        request__user=request.user, is_staff_reply=True, read_at__isnull=True
    ).select_related("request").order_by("-created_at")
    return {"support_unread_count": notifications.count(), "support_notifications": notifications[:5]}
