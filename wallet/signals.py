from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User

from .models import Wallet


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)