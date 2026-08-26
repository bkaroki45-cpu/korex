from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from wallet.models import CryptoDeposit, WithdrawalNetwork, WithdrawalRequest
from wallet.services import credit_confirmed_deposit, get_deposit_address, record_provider_deposit


class CryptoDepositTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", email="alice@example.com", password="test-password")
        self.bob = User.objects.create_user(username="bob", email="bob@example.com", password="test-password")

    def test_each_user_receives_a_distinct_persistent_address(self):
        alice_address = get_deposit_address(self.alice)
        bob_address = get_deposit_address(self.bob)
        self.assertNotEqual(alice_address.address, bob_address.address)
        self.assertEqual(get_deposit_address(self.alice).pk, alice_address.pk)

    def test_confirmed_deposit_credits_only_the_address_owner_once(self):
        address = get_deposit_address(self.alice)
        deposit, created = record_provider_deposit(recipient_address=address.address, transaction_hash="a" * 64, amount=Decimal("500"), asset="USDT", network="TRC20", status=CryptoDeposit.Status.CONFIRMED)
        self.assertTrue(created)
        self.alice.wallet.refresh_from_db()
        self.bob.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.available_balance, Decimal("500.00"))
        self.assertEqual(self.bob.wallet.available_balance, Decimal("0.00"))
        duplicate, created = record_provider_deposit(recipient_address=address.address, transaction_hash="a" * 64, amount=Decimal("500"), asset="USDT", network="TRC20", status=CryptoDeposit.Status.CONFIRMED)
        self.assertFalse(created)
        self.assertEqual(duplicate.pk, deposit.pk)
        self.alice.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.available_balance, Decimal("500.00"))

    def test_wrong_network_and_below_minimum_are_not_credited(self):
        address = get_deposit_address(self.alice)
        with self.assertRaises(ValueError):
            record_provider_deposit(recipient_address=address.address, transaction_hash="b" * 64, amount=Decimal("50"), asset="USDT", network="ERC20", status=CryptoDeposit.Status.CONFIRMED)
        deposit, _ = record_provider_deposit(recipient_address=address.address, transaction_hash="c" * 64, amount=Decimal("5"), asset="USDT", network="TRC20", status=CryptoDeposit.Status.CONFIRMED)
        self.assertEqual(deposit.status, CryptoDeposit.Status.REJECTED)
        self.alice.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.available_balance, Decimal("0.00"))


class WithdrawalRequestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="withdrawer", email="withdrawer@example.com", password="test-password")
        self.user.wallet.available_balance = Decimal("50.00")
        self.user.wallet.save(update_fields=["available_balance"])
        WithdrawalNetwork.objects.get_or_create(code="TRC20", defaults={"name": "TRON (TRC20)", "is_enabled": True})
        self.client.force_login(self.user)

    def test_request_above_withdrawable_balance_is_rejected(self):
        response = self.client.post("/wallet/withdraw/", {
            "amount": "55.00", "withdrawal_network": "TRC20", "withdrawal_address": "TExampleWalletAddress",
        })
        self.assertRedirects(response, "/wallet/withdraw/")
        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.available_balance, Decimal("50.00"))
        self.assertFalse(WithdrawalRequest.objects.filter(user=self.user).exists())

    def test_request_saves_destination_and_reserves_withdrawable_balance(self):
        response = self.client.post("/wallet/withdraw/", {
            "amount": "20.00", "withdrawal_network": "TRC20", "withdrawal_address": "TExampleWalletAddress",
        })
        self.assertRedirects(response, "/wallet/withdraw/")
        self.user.refresh_from_db()
        self.user.wallet.refresh_from_db()
        request = WithdrawalRequest.objects.get(user=self.user)
        self.assertEqual(request.address, "TExampleWalletAddress")
        self.assertEqual(self.user.withdrawal_network, "TRC20")
        self.assertEqual(self.user.wallet.available_balance, Decimal("30.00"))
