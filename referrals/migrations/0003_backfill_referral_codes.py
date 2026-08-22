import secrets

from django.db import migrations


def add_codes(apps, schema_editor):
    ReferralProfile = apps.get_model("referrals", "ReferralProfile")
    for profile in ReferralProfile.objects.filter(referral_code__isnull=True):
        code = secrets.token_urlsafe(6).upper()
        while ReferralProfile.objects.filter(referral_code=code).exists():
            code = secrets.token_urlsafe(6).upper()
        profile.referral_code = code
        profile.save(update_fields=["referral_code"])


class Migration(migrations.Migration):
    dependencies = [("referrals", "0002_referralprofile_referral_code")]
    operations = [migrations.RunPython(add_codes, migrations.RunPython.noop)]
