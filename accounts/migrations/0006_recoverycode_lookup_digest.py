from django.db import migrations, models


def invalidate_legacy_recovery_codes(apps, schema_editor):
    # Existing codes cannot be backfilled because their plaintext is deliberately
    # never stored. Users can safely generate a replacement set after upgrade.
    apps.get_model("accounts", "RecoveryCode").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_two_factor_authentication")]
    operations = [
        migrations.AddField(model_name="recoverycode", name="lookup_digest", field=models.CharField(db_index=True, default="", max_length=64), preserve_default=False),
        migrations.RunPython(invalidate_legacy_recovery_codes, migrations.RunPython.noop),
    ]
