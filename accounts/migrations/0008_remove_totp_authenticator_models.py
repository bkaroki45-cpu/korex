from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_email_verification_and_trusted_devices")]
    operations = [
        migrations.DeleteModel(name="RecoveryCode"),
        migrations.DeleteModel(name="TwoFactorSettings"),
    ]
