from django.core.management.base import BaseCommand

from investments.services import create_scheduled_signals, mark_missed_signals, mature_due_investments, settle_due_trades


class Command(BaseCommand):
    help = "Publishes Kenya's scheduled signals and returns principal for due investments."

    def handle(self, *args, **options):
        signals = create_scheduled_signals()
        missed = mark_missed_signals()
        settled = settle_due_trades()
        matured = mature_due_investments()
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(signals)} signals; marked {missed} missed; settled {settled} trades; matured {matured} trade balances."))
