from decimal import Decimal

from django.conf import settings
from django.db import models


class Transaction(models.Model):

    class TransactionType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
        PROFIT = "PROFIT", "Profit"
        LOSS = "LOSS", "Loss"
        TRANSFER = "TRANSFER", "Transfer"
        REFERRAL = "REFERRAL", "Referral Reward"
        BONUS = "BONUS", "Bonus"
        INVESTMENT = "INVESTMENT", "Investment"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    balance_before = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    balance_after = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    reference = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"