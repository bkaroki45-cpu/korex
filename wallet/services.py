import os
import secrets
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from transactions.models import Transaction
from .models import CryptoDeposit, DepositAddress, OnRampOrder, Wallet

CRYPTO_PROVIDER_MODE = os.getenv("CRYPTO_PROVIDER_MODE", "mock").lower()
CRYPTO_PROVIDER_NAME = os.getenv("CRYPTO_PROVIDER_NAME", "unconfigured")
MINIMUM_USDT_DEPOSIT = Decimal(os.getenv("MINIMUM_USDT_DEPOSIT", "10"))


class MockCustodyProvider:
    """Development-only provider. It deliberately never verifies or credits real funds."""
    name = "mock"

    def create_address(self, user, asset, network):
        return f"MOCK-{network}-{user.pk}-{secrets.token_urlsafe(12).upper()}"

    def verify_transaction(self, deposit):
        return {"status": CryptoDeposit.Status.PENDING, "note": "Mock mode cannot verify or credit a blockchain transaction."}


def custody_provider():
    # Replace this branch with a signed-webhook/custody SDK adapter when selected.
    return MockCustodyProvider()


@transaction.atomic
def get_deposit_address(user, asset="USDT", network="TRC20"):
    address = DepositAddress.objects.select_for_update().filter(user=user, asset=asset, network=network, is_active=True).first()
    if address:
        return address
    provider = custody_provider()
    return DepositAddress.objects.create(user=user, asset=asset, network=network, address=provider.create_address(user, asset, network), provider=provider.name)


@transaction.atomic
def submit_transaction_hash(*, user, transaction_hash):
    address = get_deposit_address(user)
    if CryptoDeposit.objects.filter(transaction_hash=transaction_hash).exists():
        raise ValueError("This transaction hash has already been submitted.")
    deposit = CryptoDeposit.objects.create(user=user, deposit_address=address, transaction_hash=transaction_hash, provider=address.provider if False else None)
    result = custody_provider().verify_transaction(deposit)
    deposit.status, deposit.verification_note = result["status"], result["note"]
    deposit.save(update_fields=["status", "verification_note", "updated_at"])
    return deposit


@transaction.atomic
def credit_confirmed_deposit(deposit):
    """Provider webhook adapters call this only after network/token/address confirmation."""
    deposit = CryptoDeposit.objects.select_for_update().select_related("user").get(pk=deposit.pk)
    if deposit.status != CryptoDeposit.Status.CONFIRMED or deposit.credited_at or not deposit.amount or deposit.amount < MINIMUM_USDT_DEPOSIT:
        return False
    wallet = Wallet.objects.select_for_update().get(user=deposit.user)
    amount = deposit.amount.quantize(Decimal("0.01"))
    before = wallet.available_balance
    wallet.available_balance += amount
    wallet.total_deposited += amount
    wallet.save(update_fields=["available_balance", "total_deposited", "updated_at"])
    Transaction.objects.create(user=deposit.user, transaction_type=Transaction.TransactionType.DEPOSIT, amount=amount, balance_before=before, balance_after=wallet.available_balance, reference=f"CRYPTO-DEPOSIT-{deposit.id}", description=f"Confirmed {deposit.asset} {deposit.network} deposit", status=Transaction.Status.COMPLETED, completed_at=timezone.now())
    deposit.credited_at = timezone.now()
    deposit.save(update_fields=["credited_at", "updated_at"])
    return True


def create_onramp_order(user, amount_kes):
    return OnRampOrder.objects.create(user=user, provider=CRYPTO_PROVIDER_NAME if CRYPTO_PROVIDER_MODE != "mock" else "mock", amount_kes=amount_kes, provider_reference=f"ONRAMP-{secrets.token_urlsafe(12)}", status=OnRampOrder.Status.INITIATED)
