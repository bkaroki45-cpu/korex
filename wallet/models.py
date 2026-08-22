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


class DepositAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="deposit_addresses")
    asset = models.CharField(max_length=12, default="USDT")
    network = models.CharField(max_length=20, default="TRC20")
    address = models.CharField(max_length=255, unique=True)
    provider = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "asset", "network"], name="one_active_deposit_address_per_network")]


class CryptoDeposit(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMING = "CONFIRMING", "Confirming"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crypto_deposits")
    deposit_address = models.ForeignKey(DepositAddress, on_delete=models.PROTECT, related_name="deposits")
    asset = models.CharField(max_length=12, default="USDT")
    network = models.CharField(max_length=20, default="TRC20")
    amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    transaction_hash = models.CharField(max_length=128, unique=True, null=True, blank=True)
    provider_reference = models.CharField(max_length=128, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    verification_note = models.TextField(blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class OnRampOrder(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        PENDING = "PENDING", "Pending"
        SETTLED = "SETTLED", "Settled"
        FAILED = "FAILED", "Failed"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onramp_orders")
    provider = models.CharField(max_length=50)
    amount_kes = models.DecimalField(max_digits=20, decimal_places=2)
    estimated_usdt = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    provider_reference = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    checkout_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
