from django.conf import settings
from django.db import models


class SupportRequest(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        RESOLVED = "RESOLVED", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="support_requests")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=180)
    message = models.TextField(max_length=1500)
    source_ip_hash = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} - {self.subject}"


class SupportMessage(models.Model):
    """A message in a support conversation. Staff messages create user alerts."""

    request = models.ForeignKey(SupportRequest, on_delete=models.CASCADE, related_name="replies")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="support_messages")
    body = models.TextField(max_length=1500)
    is_staff_reply = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply to #{self.request_id}"
