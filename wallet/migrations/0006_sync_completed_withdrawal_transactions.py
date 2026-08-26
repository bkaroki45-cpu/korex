from django.db import migrations
from django.utils import timezone


def sync_completed_withdrawal_transactions(apps, schema_editor):
    WithdrawalRequest = apps.get_model("wallet", "WithdrawalRequest")
    Transaction = apps.get_model("transactions", "Transaction")
    now = timezone.now()

    for withdrawal in WithdrawalRequest.objects.filter(status="COMPLETED").iterator():
        Transaction.objects.filter(
            user_id=withdrawal.user_id,
            transaction_type="WITHDRAWAL",
            reference=f"WITHDRAWAL-REQUEST-{withdrawal.id}",
        ).exclude(status="COMPLETED").update(status="COMPLETED", completed_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0001_initial"),
        ("wallet", "0005_platformconfiguration_minimum_withdrawal"),
    ]

    operations = [
        migrations.RunPython(sync_completed_withdrawal_transactions, migrations.RunPython.noop),
    ]
