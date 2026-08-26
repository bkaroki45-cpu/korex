from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import KYCVerification, User
from investments.models import EarningSession, Investment, Signal, SignalParticipation
from investments.services import eligible_signals_for_user, kenya_today, mark_missed_signals, participate_in_signal, settle_due_trades
from memberships.models import Membership


class DailySignalProfitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="investor", email="investor@example.com", password="test-password")
        KYCVerification.objects.create(user=self.user, status=KYCVerification.Status.VERIFIED)
        self.investment = Investment.objects.create(
            user=self.user, principal=Decimal("500.00"), current_value=Decimal("500.00"),
            daily_rate=Decimal("0.0200"), duration_days=35, end_date=timezone.now() + timedelta(days=35),
        )
        now = timezone.now() - timedelta(minutes=1)
        self.morning = Signal.objects.create(signal_date=kenya_today(), slot=Signal.Slot.MORNING, scheduled_at=now)
        self.afternoon = Signal.objects.create(signal_date=kenya_today(), slot=Signal.Slot.AFTERNOON, scheduled_at=now)
        self.evening = Signal.objects.create(signal_date=kenya_today(), slot=Signal.Slot.EVENING, scheduled_at=now)

    def test_regular_member_trades_the_two_regular_one_percent_signals_then_settles(self):
        first_amount, first_paid = participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.morning.id)
        second_amount, second_paid = participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.afternoon.id)
        self.user.wallet.refresh_from_db()
        self.assertEqual(first_amount, Decimal("5.00"))
        self.assertEqual(second_amount, Decimal("5.00"))
        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.total_profit, Decimal("0.00"))
        settle_due_trades(now=timezone.now() + timedelta(hours=6))
        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.total_profit, Decimal("10.00"))
        self.assertEqual(SignalParticipation.objects.count(), 2)
        self.assertEqual(
            self.investment.earning_sessions.filter(status=EarningSession.Status.TRADED).count(),
            2,
        )

    def test_everyone_can_see_team_leader_signal_but_regular_member_cannot_trade_it(self):
        self.assertIn(self.evening, eligible_signals_for_user(self.user))
        with self.assertRaisesMessage(ValueError, "Team Leaders"):
            participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.evening.id)
        membership, _ = Membership.objects.get_or_create(user=self.user)
        membership.membership_type = Membership.MembershipType.TEAM_LEADER
        membership.save(update_fields=["membership_type"])
        amount, _ = participate_in_signal(user=self.user, investment_id=self.investment.id, signal_id=self.evening.id)
        self.assertEqual(amount, Decimal("5.00"))

    def test_untraded_signal_is_marked_missed_after_thirty_minutes(self):
        self.morning.scheduled_at = timezone.now() + timedelta(minutes=1)
        self.morning.save(update_fields=["scheduled_at"])
        mark_missed_signals(now=timezone.now() + timedelta(minutes=32))
        self.assertTrue(self.investment.earning_sessions.filter(signal=self.morning, status="MISSED").exists())

# Create your tests here.
