from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

from accounts.models import User

from .models import Membership


@receiver(post_save, sender=User)
def create_user_membership(sender, instance, created, **kwargs):

    if created:
        Membership.objects.create(
            user=instance,
            membership_type=Membership.MembershipType.REGULAR,
            daily_sessions=2,
            earning_rate=Decimal("0.0200"),
        )
