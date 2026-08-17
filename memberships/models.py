from django.conf import settings
from django.db import models


class Membership(models.Model):

    class MembershipType(models.TextChoices):
        BASIC = "BASIC", "Basic"
        TEAM = "TEAM", "Team"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership",
    )

    membership_type = models.CharField(
        max_length=20,
        choices=MembershipType.choices,
        default=MembershipType.BASIC,
    )

    daily_sessions = models.PositiveIntegerField(
        default=3,
    )

    is_active = models.BooleanField(
        default=True,
    )

    activated_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.user.email} - {self.membership_type}"