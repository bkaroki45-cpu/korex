from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_recoverycode_lookup_digest")]
    operations = [
        migrations.CreateModel(name="EmailVerificationCode", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("code_hash", models.CharField(max_length=256)),
            ("expires_at", models.DateTimeField(db_index=True)), ("attempts", models.PositiveSmallIntegerField(default=0)),
            ("used_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_verification_codes", to=settings.AUTH_USER_MODEL)),
        ], options={"indexes": [models.Index(fields=["user", "used_at", "expires_at"], name="accounts_ev_user_id_7aa99a_idx")] }),
        migrations.CreateModel(name="TrustedDevice", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("token_hash", models.CharField(max_length=64, unique=True)),
            ("label", models.CharField(blank=True, max_length=180)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("last_used_at", models.DateTimeField(auto_now=True)), ("expires_at", models.DateTimeField(db_index=True)), ("revoked_at", models.DateTimeField(blank=True, null=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="trusted_devices", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-last_used_at"], "indexes": [models.Index(fields=["user", "revoked_at", "expires_at"], name="accounts_td_user_id_f1f7fd_idx")] }),
    ]
