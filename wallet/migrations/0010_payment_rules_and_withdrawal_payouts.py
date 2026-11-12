from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wallet", "0009_mpesadeposit_amount_usdt_mpesadeposit_credited_at_and_more")]
    operations = [
        migrations.AlterField(model_name="platformconfiguration", name="minimum_deposit", field=models.DecimalField(decimal_places=2, default=Decimal("10.00"), max_digits=20)),
        migrations.AddField(model_name="platformconfiguration", name="signal_minimum_balance", field=models.DecimalField(decimal_places=2, default=Decimal("500.00"), max_digits=20)),
        migrations.AddField(model_name="platformconfiguration", name="withdrawal_fee_percent", field=models.DecimalField(decimal_places=2, default=Decimal("10.00"), max_digits=5)),
        migrations.AddField(model_name="withdrawalrequest", name="fee_amount", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=20)),
        migrations.AddField(model_name="withdrawalrequest", name="payout_amount", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=20)),
        migrations.RunPython(lambda apps, schema_editor: apps.get_model("wallet", "PlatformConfiguration").objects.filter(pk=1).update(minimum_deposit=Decimal("10.00")), migrations.RunPython.noop),
    ]
