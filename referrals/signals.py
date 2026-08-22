from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User

from .models import ReferralProfile
from .services import new_referral_code


@receiver(post_save, sender=User)
def create_referral_profile(sender, instance, created, **kwargs):

    if created:
        ReferralProfile.objects.create(user=instance, referral_code=new_referral_code())
