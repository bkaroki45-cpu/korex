import secrets

from django.db import migrations


def sync_referral_codes(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    ReferralProfile = apps.get_model("referrals", "ReferralProfile")

    def next_code():
        while True:
            code = secrets.token_urlsafe(6).upper()
            if not ReferralProfile.objects.filter(referral_code=code).exists() and not User.objects.filter(referral_code=code).exists():
                return code

    for user in User.objects.all().iterator():
        profile, _ = ReferralProfile.objects.get_or_create(user=user)
        code = profile.referral_code or user.referral_code or next_code()
        if ReferralProfile.objects.exclude(pk=profile.pk).filter(referral_code=code).exists() or User.objects.exclude(pk=user.pk).filter(referral_code=code).exists():
            code = next_code()
        if profile.referral_code != code:
            profile.referral_code = code
            profile.save(update_fields=["referral_code"])
        if user.referral_code != code:
            User.objects.filter(pk=user.pk).update(referral_code=code)


class Migration(migrations.Migration):
    dependencies = [("referrals", "0003_backfill_referral_codes")]
    operations = [migrations.RunPython(sync_referral_codes, migrations.RunPython.noop)]
