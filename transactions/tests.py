from decimal import Decimal

from django.test import TestCase

from accounts.models import User
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

# Create your tests here.
