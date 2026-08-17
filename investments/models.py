from decimal import Decimal

from django.conf import settings
from django.db import models


class Investment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investments",
    )

    principal = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    current_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    daily_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0200"),
    )

    duration_days = models.PositiveIntegerField(
        default=30,
    )

    start_date = models.DateTimeField(
        auto_now_add=True,
    )

    end_date = models.DateTimeField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    total_profit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Investment #{self.id} - {self.user.email}"

    @property
    def daily_profit(self):
        return self.current_value * self.daily_rate


class EarningSession(models.Model):

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        PARTICIPATED = "PARTICIPATED", "Participated"
        EXPIRED = "EXPIRED", "Expired"

    investment = models.ForeignKey(
        Investment,
        on_delete=models.CASCADE,
        related_name="earning_sessions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earning_sessions",
    )

    session_date = models.DateField()

    display_asset = models.CharField(
        max_length=30,
        default="BTC/USDT",
    )

    display_direction = models.CharField(
        max_length=10,
        choices=[
            ("BUY", "BUY"),
            ("SELL", "SELL"),
        ],
        default="BUY",
    )

    display_entry_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
    )

    display_take_profit = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
    )

    display_stop_loss = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
    )

    earning_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.0200"),
    )

    earning_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    participated_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.display_asset} - "
            f"{self.session_date}"
        )