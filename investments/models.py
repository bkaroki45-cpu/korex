from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Investment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investments")
    principal = models.DecimalField(max_digits=20, decimal_places=2)
    current_value = models.DecimalField(max_digits=20, decimal_places=2)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0200"))
    duration_days = models.PositiveIntegerField(default=35)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    total_profit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Investment #{self.id} - {self.user.email}"

    @property
    def daily_profit(self):
        # Earnings are based on locked principal and never compound automatically.
        return self.principal * self.daily_rate

    @property
    def remaining_days(self):
        if not self.end_date or self.status != self.Status.ACTIVE:
            return 0
        return max(0, (self.end_date.date() - timezone.localdate()).days)

    @property
    def today_earned(self):
        session = self.earning_sessions.filter(session_date=timezone.localdate(), status="PARTICIPATED").first()
        return session.earning_amount if session else Decimal("0.00")


class Signal(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CANCELLED = "CANCELLED", "Cancelled"

    class Slot(models.TextChoices):
        MORNING = "MORNING", "10:00 AM"
        AFTERNOON = "AFTERNOON", "3:00 PM"
        EVENING = "EVENING", "9:00 PM"

    signal_date = models.DateField()
    slot = models.CharField(max_length=10, choices=Slot.choices)
    scheduled_at = models.DateTimeField()
    pair = models.CharField(max_length=30, default="BTC/USDT")
    direction = models.CharField(max_length=10, choices=[("BUY", "BUY"), ("SELL", "SELL")], default="BUY")
    entry_price = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]
        constraints = [models.UniqueConstraint(fields=["signal_date", "slot"], name="unique_signal_slot_per_day")]

    def __str__(self):
        return f"{self.pair} {self.slot} {self.signal_date}"


class EarningSession(models.Model):
    """Immutable payout ledger for a specific investment and published signal."""
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        PARTICIPATED = "PARTICIPATED", "Participated"
        EXPIRED = "EXPIRED", "Expired"

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name="earning_sessions")
    signal = models.ForeignKey(Signal, on_delete=models.SET_NULL, related_name="earning_sessions", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="earning_sessions")
    session_date = models.DateField()
    display_asset = models.CharField(max_length=30, default="BTC/USDT")
    display_direction = models.CharField(max_length=10, choices=[("BUY", "BUY"), ("SELL", "SELL")], default="BUY")
    display_entry_price = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    display_take_profit = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    display_stop_loss = models.DecimalField(max_digits=20, decimal_places=8, blank=True, null=True)
    earning_rate = models.DecimalField(max_digits=8, decimal_places=4, default=Decimal("0.0200"))
    earning_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    participated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["investment", "signal"], name="one_payout_per_investment_signal")]


class SignalParticipation(models.Model):
    """An immutable record that a user touched a particular published signal."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signal_participations")
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE, related_name="signal_participations")
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name="participations")
    participated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "investment", "signal"], name="one_participation_per_signal_investment"),
            models.CheckConstraint(condition=Q(investment__isnull=False), name="participation_has_investment"),
        ]
