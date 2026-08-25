from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets


class User(AbstractUser):
    email = models.EmailField(unique=True)

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    country = models.CharField(max_length=100, blank=True, default="")

    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    referral_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="referrals"
    )

    is_verified = models.BooleanField(default=False)

    account_id = models.CharField(max_length=16, unique=True, editable=False, blank=True)
    withdrawal_address = models.CharField(max_length=255, blank=True)
    withdrawal_network = models.CharField(max_length=32, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.account_id:
            while True:
                candidate = f"CDD-{secrets.randbelow(900000) + 100000}"
                if not type(self).objects.filter(account_id=candidate).exists():
                    self.account_id = candidate
                    break
        super().save(*args, **kwargs)
