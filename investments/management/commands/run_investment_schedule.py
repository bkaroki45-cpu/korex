from django.core.management.base import BaseCommand

from investments.services import create_scheduled_signals, mature_due_investments


class Command(BaseCommand):
    help = "Publishes Kenya's scheduled signals and returns principal for due investments."

    def handle(self, *args, **options):
        signals = create_scheduled_signals()
        matured = mature_due_investments()
        self.stdout.write(self.style.SUCCESS(f"Ensured {len(signals)} scheduled signals; matured {matured} investments."))
