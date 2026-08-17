from decimal import Decimal

from django.conf import settings
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    available_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    locked_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_profit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_deposited = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_withdrawn = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00")
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} Wallet"

    @property
    def total_balance(self):
        return self.available_balance + self.locked_balance