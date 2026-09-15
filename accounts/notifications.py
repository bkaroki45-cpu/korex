"""Member-facing transactional email notifications."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
from django.utils import timezone

logger = logging.getLogger(__name__)


def _member_name(user):
    return user.get_full_name().strip() or user.first_name or "Member"


def _send(user, subject, text_body, html_body):
    """Send a notification without allowing an email outage to stop a payment flow."""
    if not user.email:
        return
    try:
        message = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
    except Exception:
        logger.exception("Could not send transactional email to user %s", user.pk)


def _html_page(title, greeting, intro, rows, closing):
    detail_rows = "".join(
        f'<tr><td style="padding:8px 12px;color:#6b7280;border-bottom:1px solid #e5e7eb">{escape(str(label))}</td>'
        f'<td style="padding:8px 12px;color:#111827;font-weight:600;border-bottom:1px solid #e5e7eb">{escape(str(value))}</td></tr>'
        for label, value in rows
    )
    return f"""<!doctype html><html><body style="margin:0;background:#f3f6fa;font-family:Arial,sans-serif;color:#172033">
<div style="max-width:620px;margin:28px auto;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #dde5ef">
<div style="padding:22px 28px;background:#071c33;color:#ffffff"><strong style="font-size:20px">CLOUDD 1</strong></div>
<div style="padding:28px"><h1 style="margin:0 0 16px;font-size:24px">{title}</h1><p>{greeting}</p><p>{intro}</p>
<table style="width:100%;border-collapse:collapse;margin:20px 0;background:#f9fbfd">{detail_rows}</table>
<p>{closing}</p><p style="margin-top:24px">Regards,<br><strong>The CLOUDD 1 Team</strong></p></div></div></body></html>"""


def send_welcome_email(user):
    name = _member_name(user)
    subject = "Welcome to CLOUDD 1"
    text = (
        f"Hello {name},\n\nWelcome to CLOUDD 1. Your account has been created successfully. "
        "Please keep your account secure and complete the email verification step to access your member console.\n\n"
        f"Account ID: {user.account_id}\nEmail: {user.email}\n\n"
        "We are pleased to have you with us.\n\nRegards,\nThe CLOUDD 1 Team"
    )
    html = _html_page("Welcome to CLOUDD 1", f"Hello {name},", "Your account has been created successfully. Please verify your email to access your member console.", [("Account ID", user.account_id), ("Email", user.email)], "We are pleased to have you with us. Keep your sign-in details private and never share verification codes.")
    _send(user, subject, text, html)


def send_deposit_success_email(deposit, *, reference):
    user = deposit.user
    name = _member_name(user)
    amount = f"{deposit.amount:,.2f} {deposit.asset}"
    completed_at = deposit.approved_at or deposit.credited_at or deposit.confirmed_at or timezone.now()
    subject = "Your CLOUDD 1 deposit was successful"
    text = (
        f"Hello {name},\n\nYour deposit has been successfully confirmed and recorded in your CLOUDD 1 account.\n\n"
        f"Account ID: {user.account_id}\nAmount: {amount}\nNetwork: {deposit.network}\nReference: {reference}\n"
        f"Transaction ID: {deposit.transaction_hash or 'Not provided'}\nCompleted: {completed_at:%d %b %Y, %H:%M %Z}\n\n"
        "You can review your balance and activity from your member console.\n\nRegards,\nThe CLOUDD 1 Team"
    )
    html = _html_page("Deposit successful", f"Hello {name},", "Your deposit has been confirmed and recorded in your CLOUDD 1 account.", [("Account ID", user.account_id), ("Amount", amount), ("Network", deposit.network), ("Reference", reference), ("Transaction ID", deposit.transaction_hash or "Not provided"), ("Completed", completed_at.strftime("%d %b %Y, %H:%M %Z"))], "You can review your balance and activity from your member console.")
    _send(user, subject, text, html)


def send_withdrawal_success_email(withdrawal):
    user = withdrawal.user
    name = _member_name(user)
    amount = f"{withdrawal.amount:,.2f} {withdrawal.asset}"
    completed_at = withdrawal.completed_at or timezone.now()
    subject = "Your CLOUDD 1 withdrawal was successful"
    text = (
        f"Hello {name},\n\nYour withdrawal has been successfully processed.\n\n"
        f"Account ID: {user.account_id}\nAmount: {amount}\nNetwork: {withdrawal.network}\n"
        f"Destination address: {withdrawal.address}\nReference: WITHDRAWAL-REQUEST-{withdrawal.id}\n"
        f"Completed: {completed_at:%d %b %Y, %H:%M %Z}\n\n"
        "Please allow for the selected network's normal confirmation time.\n\nRegards,\nThe CLOUDD 1 Team"
    )
    html = _html_page("Withdrawal successful", f"Hello {name},", "Your withdrawal has been successfully processed.", [("Account ID", user.account_id), ("Amount", amount), ("Network", withdrawal.network), ("Destination address", withdrawal.address), ("Reference", f"WITHDRAWAL-REQUEST-{withdrawal.id}"), ("Completed", completed_at.strftime("%d %b %Y, %H:%M %Z"))], "Please allow for the selected network's normal confirmation time.")
    _send(user, subject, text, html)
