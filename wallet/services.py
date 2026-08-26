import os
import secrets
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from transactions.models import Transaction
from .models import CryptoDeposit, DepositAddress, OnRampOrder, PlatformConfiguration, Wallet, WithdrawalRequest

CRYPTO_PROVIDER_MODE = os.getenv("CRYPTO_PROVIDER_MODE", "mock").lower()
CRYPTO_PROVIDER_NAME = os.getenv("CRYPTO_PROVIDER_NAME", "unconfigured")
MINIMUM_USDT_DEPOSIT = Decimal(os.getenv("MINIMUM_USDT_DEPOSIT", "500"))


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
    deposit = CryptoDeposit.objects.create(user=user, deposit_address=address, transaction_hash=transaction_hash)
    result = custody_provider().verify_transaction(deposit)
    deposit.status, deposit.verification_note = result["status"], result["note"]
    deposit.save(update_fields=["status", "verification_note", "updated_at"])
    return deposit


@transaction.atomic
def submit_manual_deposit(*, user, amount, transaction_hash, proof=None):
    config = PlatformConfiguration.current()
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount < config.minimum_deposit:
        raise ValueError(f"Minimum deposit is ${config.minimum_deposit:.0f}.")
    if len(transaction_hash.strip()) < 20:
        raise ValueError("Enter a valid transaction ID.")
    if CryptoDeposit.objects.filter(transaction_hash=transaction_hash.strip()).exists():
        raise ValueError("This transaction ID has already been submitted.")
    # Retain the existing address record for compatibility; the configured receiving address is immutable on the deposit.
    address = get_deposit_address(user, config.deposit_asset, config.deposit_network)
    return CryptoDeposit.objects.create(user=user, deposit_address=address, asset=config.deposit_asset,
        network=config.deposit_network, amount=amount, transaction_hash=transaction_hash.strip(), proof=proof,
        receiving_address=config.deposit_address, status=CryptoDeposit.Status.PENDING)


@transaction.atomic
def approve_manual_deposit(*, deposit_id, admin_user):
    """The sole credit/activation path for a manually verified deposit."""
    deposit = CryptoDeposit.objects.select_for_update().select_related("user").get(pk=deposit_id)
    config = PlatformConfiguration.current()
    if deposit.status != CryptoDeposit.Status.PENDING:
        raise ValueError("This deposit was already processed.")
    if not deposit.amount or deposit.amount < config.minimum_deposit:
        raise ValueError("This deposit does not meet the qualifying minimum.")
    from investments.models import Investment
    from referrals.services import grant_deposit_rewards, refresh_referrer_status
    wallet = Wallet.objects.select_for_update().get(user=deposit.user)
    now = timezone.now()
    deposit.status, deposit.approved_by, deposit.approved_at, deposit.confirmed_at = CryptoDeposit.Status.COMPLETED, admin_user, now, now
    deposit.save(update_fields=["status", "approved_by", "approved_at", "confirmed_at", "updated_at"])
    wallet.locked_balance += deposit.amount
    wallet.total_deposited += deposit.amount
    wallet.save(update_fields=["locked_balance", "total_deposited", "updated_at"])
    investment = Investment.objects.create(user=deposit.user, deposit=deposit, principal=deposit.amount, current_value=deposit.amount,
        daily_rate=Decimal("0.0100"), duration_days=config.principal_lock_days, end_date=now + timedelta(days=config.principal_lock_days), status=Investment.Status.ACTIVE)
    Transaction.objects.create(user=deposit.user, transaction_type=Transaction.TransactionType.DEPOSIT, amount=deposit.amount,
        balance_before=wallet.available_balance, balance_after=wallet.available_balance, reference=f"MANUAL-DEPOSIT-{deposit.id}",
        description=f"Approved {deposit.asset} {deposit.network} deposit; principal locked", status=Transaction.Status.COMPLETED, completed_at=now)
    grant_deposit_rewards(deposit=deposit)
    try:
        refresh_referrer_status(deposit.user.received_referral.referrer)
    except Exception:
        pass
    return investment


@transaction.atomic
def complete_withdrawal(*, withdrawal_id, admin_user):
    withdrawal = WithdrawalRequest.objects.select_for_update().select_related("user").get(pk=withdrawal_id)
    now = timezone.now()
    ledger_entries = Transaction.objects.select_for_update().filter(
        user=withdrawal.user,
        transaction_type=Transaction.TransactionType.WITHDRAWAL,
        reference=f"WITHDRAWAL-REQUEST-{withdrawal.id}",
    )
    if withdrawal.status == WithdrawalRequest.Status.REJECTED:
        raise ValueError("A rejected withdrawal cannot be completed.")

    # Retrying a completed request repairs a stale pending ledger entry without
    # counting the same withdrawal in the wallet total a second time.
    if withdrawal.status == WithdrawalRequest.Status.PENDING:
        wallet = Wallet.objects.select_for_update().get(user=withdrawal.user)
        wallet.total_withdrawn += withdrawal.amount
        wallet.save(update_fields=["total_withdrawn", "updated_at"])
        withdrawal.status, withdrawal.completed_by, withdrawal.completed_at = WithdrawalRequest.Status.COMPLETED, admin_user, now
        withdrawal.save(update_fields=["status", "completed_by", "completed_at"])

    ledger_entries.update(
        status=Transaction.Status.COMPLETED,
        completed_at=now,
        description="Manually completed withdrawal",
    )
    return withdrawal


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


@transaction.atomic
def record_provider_deposit(*, recipient_address, transaction_hash, amount, asset, network, status, provider_reference=None):
    """Entry point for a real provider webhook after its signature is verified.

    A future provider adapter must supply values obtained from the provider/blockchain,
    never values received directly from a browser form.
    """
    try:
        amount = Decimal(str(amount))
    except Exception as error:
        raise ValueError("Provider amount is invalid.") from error
    if status not in CryptoDeposit.Status.values:
        raise ValueError("Provider status is invalid.")
    address = DepositAddress.objects.select_for_update().select_related("user").filter(address=recipient_address, asset=asset, network=network, is_active=True).first()
    if not address:
        raise ValueError("Recipient address is not an active CLOUDD 1 deposit address.")
    deposit, created = CryptoDeposit.objects.select_for_update().get_or_create(
        transaction_hash=transaction_hash,
        defaults={"user": address.user, "deposit_address": address, "asset": asset, "network": network,
                  "amount": amount, "provider_reference": provider_reference, "status": status},
    )
    if not created:
        return deposit, False
    if amount < MINIMUM_USDT_DEPOSIT:
        deposit.status, deposit.verification_note = CryptoDeposit.Status.REJECTED, "Deposit is below the minimum amount."
    elif status == CryptoDeposit.Status.CONFIRMED:
        deposit.confirmed_at = timezone.now()
    deposit.save()
    if deposit.status == CryptoDeposit.Status.CONFIRMED:
        credit_confirmed_deposit(deposit)
    return deposit, True
