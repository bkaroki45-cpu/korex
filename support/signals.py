from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from accounts.models import User
from wallet.models import CryptoDeposit, WithdrawalRequest
from transactions.models import Transaction

from .models import SupportRequest
from .telegram import send_alert


def username(user):
    return user.username or "—"


@receiver(post_save, sender=User)
def alert_new_user(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_alert(
            f"🆕 New website user\nName: {instance.get_full_name() or '—'}\nUsername: @{username(instance)}\nUser ID: {instance.account_id}\nEmail: {instance.email}"
        ))


@receiver(post_save, sender=CryptoDeposit)
def alert_deposit(sender, instance, created, **kwargs):
    if created:
        transaction_type = "Manual transaction" if instance.receiving_address else "Normal transaction"
        transaction.on_commit(lambda: send_alert(
            f"💳 Deposit request ({transaction_type})\nAmount: {instance.amount or 'Pending'} {instance.asset}\nTransaction ID: {instance.transaction_hash or '—'}\nUser ID: {instance.user.account_id}\nUsername: @{username(instance.user)}\nStatus: {instance.get_status_display()}"
        ))


@receiver(post_save, sender=Transaction)
def alert_admin_manual_transaction(sender, instance, created, **kwargs):
    if created and instance.reference.startswith("ADMIN-DEPOSIT-"):
        transaction.on_commit(lambda: send_alert(
            f"🛠️ Manual transaction by admin\nAmount: {instance.amount}\nTransaction ID: {instance.reference}\nUser ID: {instance.user.account_id}\nUsername: @{username(instance.user)}\nStatus: {instance.get_status_display()}"
        ))


@receiver(post_save, sender=WithdrawalRequest)
def alert_withdrawal(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_alert(
            f"💸 Withdrawal request\nAmount: {instance.amount} {instance.asset}\nUser ID: {instance.user.account_id}\nUsername: @{username(instance.user)}\nNetwork: {instance.network}\nWallet: {instance.address}\nStatus: {instance.get_status_display()}"
        ))


@receiver(post_save, sender=SupportRequest)
def alert_support_request(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_alert(
            f"🛟 New website support request #{instance.pk}\nFrom: {instance.name} ({instance.email})\nSubject: {instance.subject}\nMessage: {instance.message}"
        ))
