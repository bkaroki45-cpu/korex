from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name="SupportRequest",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=150)), ("email", models.EmailField(max_length=254)),
            ("subject", models.CharField(max_length=180)), ("message", models.TextField()),
            ("status", models.CharField(choices=[("OPEN", "Open"), ("IN_PROGRESS", "In progress"), ("RESOLVED", "Resolved")], default="OPEN", max_length=20)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="support_requests", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]},
    )]
