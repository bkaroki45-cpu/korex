from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from investments.models import Investment, Signal, SignalParticipation
from investments.services import kenya_today, participate_in_signal


class DailySignalProfitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="investor", email="investor@example.com", password="test-password")
        self.investment = Investment.objects.create(
            user=self.user, principal=Decimal("500.00"), current_value=Decimal("500.00"),
            daily_rate=Decimal("0.0200"), duration_days=35, end_date=timezone.now() + timedelta(days=35),
        )
        now = timezone.now() - timedelta(minutes=1)
        self.morning = Signal.objects.create(signal_date=kenya_today(), slot=Signal.Slot.MORNING, scheduled_at=now)
        self.evening = Signal.objects.create(signal_date=kenya_today(), slot=Signal.Slot.EVENING, scheduled_at=now)

    def test_regular_member_can_earn_from_two_daily_signals(self):
        first_amount, first_paid = participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.morning.id)
        second_amount, second_paid = participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.evening.id)
        self.user.wallet.refresh_from_db()
        self.assertEqual((first_amount, first_paid), (Decimal("10.00"), True))
        self.assertEqual((second_amount, second_paid), (Decimal("10.00"), True))
        self.assertEqual(self.user.wallet.total_profit, Decimal("20.00"))
        self.assertEqual(SignalParticipation.objects.count(), 2)

# Create your tests here.
