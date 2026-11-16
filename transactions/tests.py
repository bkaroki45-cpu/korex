from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from referrals.services import create_referral
from django.urls import reverse
from .models import Transaction
from .services import create_manual_locked_deposit


class TransactionHistoryTests(TestCase):
    def test_history_shows_all_transaction_types_only_for_the_signed_in_user(self):
        user = User.objects.create_user(username="history-user", email="history@example.com", password="test-password")
        other_user = User.objects.create_user(username="other-user", email="other@example.com", password="test-password")
        for index, transaction_type in enumerate((
            Transaction.TransactionType.DEPOSIT,
            Transaction.TransactionType.WITHDRAWAL,
            Transaction.TransactionType.REFUND,
        )):
            Transaction.objects.create(
                user=user,
                transaction_type=transaction_type,
                amount=Decimal("10.00"),
                reference=f"HISTORY-{index}",
                status=Transaction.Status.COMPLETED,
            )
        Transaction.objects.create(
            user=other_user,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=Decimal("20.00"),
            reference="OTHER-USER",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("transactions:history"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 3)
        for reference in ("HISTORY-0", "HISTORY-1", "HISTORY-2"):
            self.assertContains(response, reference)
        self.assertNotContains(response, "OTHER-USER")

    def test_history_can_filter_by_transaction_type(self):
        user = User.objects.create_user(username="filter-user", email="filter@example.com", password="test-password")
        Transaction.objects.create(user=user, transaction_type=Transaction.TransactionType.DEPOSIT, amount=Decimal("10.00"), reference="FILTER-DEPOSIT")
        Transaction.objects.create(user=user, transaction_type=Transaction.TransactionType.WITHDRAWAL, amount=Decimal("12.00"), reference="FILTER-WITHDRAWAL")
        self.client.force_login(user)

        response = self.client.get(reverse("transactions:history"), {"type": Transaction.TransactionType.WITHDRAWAL})

        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "FILTER-WITHDRAWAL")
        self.assertNotContains(response, "FILTER-DEPOSIT")


class ManualDepositTests(TestCase):
    def test_admin_manual_deposit_locks_principal_and_creates_ledger_entry(self):
        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="StrongPassword123!")
        member = User.objects.create_user(username="member", email="member@example.com", password="StrongPassword123!")

        transaction = create_manual_locked_deposit(
            user=member, amount="500.00", admin_user=admin, description="Admin verified deposit",
        )

        member.wallet.refresh_from_db()
        self.assertEqual(member.wallet.locked_balance, Decimal("500.00"))
        self.assertEqual(member.wallet.total_deposited, Decimal("500.00"))
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.DEPOSIT)
        self.assertEqual(transaction.status, Transaction.Status.COMPLETED)
        self.assertTrue(member.investments.filter(principal=Decimal("500.00"), status="ACTIVE").exists())

    def test_manual_activation_credits_referrer_withdrawable_reward(self):
        admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="StrongPassword123!")
        referrer = User.objects.create_user(username="referrer", email="referrer@example.com", password="StrongPassword123!")
        member = User.objects.create_user(username="member", email="member@example.com", password="StrongPassword123!")
        create_referral(referred_user=member, referral_code=referrer.referral_profile.referral_code)

        create_manual_locked_deposit(user=member, amount="500.00", admin_user=admin)

        referrer.wallet.refresh_from_db()
        referrer.referral_profile.refresh_from_db()
        self.assertEqual(referrer.wallet.available_balance, Decimal("40.00"))
        self.assertEqual(referrer.referral_profile.referral_earnings, Decimal("40.00"))
        self.assertTrue(Transaction.objects.filter(user=referrer, transaction_type=Transaction.TransactionType.REFERRAL).exists())

# Create your tests here.
