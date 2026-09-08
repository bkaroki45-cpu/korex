from django.db import migrations, models


def set_signal_window_to_30_minutes(apps, schema_editor):
    PlatformConfiguration = apps.get_model("wallet", "PlatformConfiguration")
    PlatformConfiguration.objects.update_or_create(pk=1, defaults={"signal_window_minutes": 30})


class Migration(migrations.Migration):
    dependencies = [("wallet", "0006_sync_completed_withdrawal_transactions")]

    operations = [
        migrations.AlterField(
            model_name="platformconfiguration",
            name="signal_window_minutes",
            field=models.PositiveIntegerField(default=30),
        ),
        migrations.RunPython(set_signal_window_to_30_minutes, migrations.RunPython.noop),
    ]
