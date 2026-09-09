from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_diditwebhookevent_kycverification")]
    operations = [
        migrations.CreateModel(name="AuthenticationThrottle", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("identifier_hash", models.CharField(max_length=64)), ("purpose", models.CharField(max_length=24)),
            ("failures", models.PositiveSmallIntegerField(default=0)), ("locked_until", models.DateTimeField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
        ]),
        migrations.CreateModel(name="TwoFactorSettings", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("encrypted_secret", models.TextField(blank=True)), ("is_enabled", models.BooleanField(default=False)), ("enabled_at", models.DateTimeField(blank=True, null=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="two_factor", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="RecoveryCode", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("code_hash", models.CharField(max_length=256)), ("used_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("two_factor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recovery_codes", to="accounts.twofactorsettings")),
        ]),
        migrations.AddConstraint(model_name="authenticationthrottle", constraint=models.UniqueConstraint(fields=("identifier_hash", "purpose"), name="unique_auth_throttle")),
    ]
