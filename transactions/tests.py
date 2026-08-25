from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from referrals.services import create_referral
from .models import Transaction
from .services import create_manual_locked_deposit


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
