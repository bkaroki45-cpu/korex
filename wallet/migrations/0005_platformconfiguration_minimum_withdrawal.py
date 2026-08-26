from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wallet", "0004_seed_withdrawal_networks")]

    operations = [
        migrations.AddField(
            model_name="platformconfiguration",
            name="minimum_withdrawal",
            field=models.DecimalField(decimal_places=2, default=Decimal("10.00"), max_digits=20),
        ),
    ]
