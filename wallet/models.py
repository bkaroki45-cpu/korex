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


class WithdrawalNetwork(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PlatformConfiguration(models.Model):
    minimum_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("500.00"))
    deposit_asset = models.CharField(max_length=12, default="USDT")
    deposit_network = models.CharField(max_length=32, default="TRC20")
    deposit_address = models.CharField(max_length=255, default="TLsHkop8XAc5dafJUAEEaQ9MMBNptnr1Vf")
    principal_lock_days = models.PositiveIntegerField(default=39)
    signal_window_minutes = models.PositiveIntegerField(default=15)
    settlement_minutes = models.PositiveIntegerField(default=45)
    team_leader_requirement = models.PositiveIntegerField(default=5)

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(pk=1)[0]


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
        COMPLETED = "COMPLETED", "Completed"
        CONFIRMED = "CONFIRMED", "Confirmed"  # legacy provider state
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
    receiving_address = models.CharField(max_length=255, blank=True)
    proof = models.FileField(upload_to="deposit_proofs/", blank=True, null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_deposits")
    approved_at = models.DateTimeField(null=True, blank=True)
    credited_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    asset = models.CharField(max_length=12, default="USDT")
    address = models.CharField(max_length=255)
    network = models.CharField(max_length=32)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="completed_withdrawals")
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
