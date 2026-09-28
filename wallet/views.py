import hashlib
import hmac
import json
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import CryptoDeposit, MpesaDeposit, PlatformConfiguration, WithdrawalNetwork, WithdrawalRequest, Wallet
from transactions.models import Transaction
from .services import CRYPTO_PROVIDER_MODE, credit_confirmed_mpesa_deposit, get_deposit_address, record_provider_deposit, submit_manual_deposit
from .mpesa import MpesaError, configured as mpesa_configured, initiate_stk_push, normalize_phone, query_stk_status, quote_usdt_purchase
from accounts.kyc import is_kyc_verified
from support.telegram import send_alert


def _masked_phone(phone_number):
    """Keep admin alerts useful without exposing a member's full phone number."""
    return f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "Hidden"


def _alert_mpesa_prompt(deposit):
    send_alert(
        "M-Pesa payment prompt requested\n"
        f"Amount: KES {deposit.amount_kes:,.0f} for {deposit.amount_usdt:,.2f} USDT\n"
        f"Rate: {deposit.rate_kes_per_usdt} KES/USDT\n"
        f"User ID: {deposit.user.account_id}\n"
        f"Email: {deposit.user.email}\n"
        f"Phone: {_masked_phone(deposit.phone_number)}\n"
        f"Reference: MPESA-DEPOSIT-{deposit.id}\n"
        "Status: Prompt sent — awaiting payment confirmation"
    )


def _alert_mpesa_confirmed(deposit):
    send_alert(
        "M-Pesa payment confirmed\n"
        f"Amount received: KES {deposit.paid_amount_kes:,.2f}\n"
        f"USDT amount: {deposit.amount_usdt:,.2f} USDT\n"
        f"User ID: {deposit.user.account_id}\n"
        f"Email: {deposit.user.email}\n"
        f"Receipt: {deposit.receipt_number or '-'}\n"
        f"Reference: MPESA-DEPOSIT-{deposit.id}\n"
        "Status: Confirmed"
    )


@login_required
def deposit_options(request):
    return render(request, "wallet/deposit_options.html")


@login_required
def deposit_crypto(request):
    config = PlatformConfiguration.current()
    address = get_deposit_address(request.user, config.deposit_asset, config.deposit_network)
    deposits = CryptoDeposit.objects.filter(user=request.user).select_related("deposit_address")[:15]
    return render(request, "wallet/deposit_crypto.html", {"address": address, "config": config, "deposits": deposits, "minimum_deposit": config.minimum_deposit, "mock_mode": False})


@login_required
@require_POST
def verify_transaction_hash(request):
    txid = request.POST.get("transaction_hash", "").strip()
    proof = request.FILES.get("proof")
    if proof and (proof.size > 5 * 1024 * 1024 or not proof.content_type.startswith("image/")):
        messages.error(request, "Proof must be an image smaller than 5 MB.")
        return redirect("wallet:deposit_crypto")
    try:
        submit_manual_deposit(user=request.user, amount=request.POST.get("amount", ""), transaction_hash=txid, proof=proof)
    except (ValueError, TypeError, InvalidOperation) as error:
        messages.error(request, str(error) or "Enter a valid deposit amount.")
    else:
        messages.success(request, "Deposit submitted successfully. Status: Pending Verification.")
    return redirect("wallet:deposit_crypto")


@login_required
def request_withdrawal(request):
    if not is_kyc_verified(request.user):
        messages.error(request, "Identity verification required. Please complete KYC verification before making a withdrawal.")
        return redirect("kyc")
    config = PlatformConfiguration.current()
    networks = WithdrawalNetwork.objects.filter(is_enabled=True).order_by("name")
    if request.method == "GET":
        return render(request, "wallet/withdraw.html", {
            "wallet": request.user.wallet, "requests": request.user.withdrawal_requests.order_by("-created_at")[:10],
            "config": config, "networks": networks,
        })
    try:
        amount = Decimal(request.POST.get("amount", "")).quantize(Decimal("0.01"))
    except Exception:
        messages.error(request, "Enter a valid withdrawal amount.")
        return redirect("wallet:request_withdrawal")
    address = request.POST.get("withdrawal_address", "").strip()
    network = request.POST.get("withdrawal_network", "").strip()
    manual_payout_channels = {"MPESA", "EAST_AFRICA"}
    if network == "MPESA":
        try:
            address = f"M-PESA:{normalize_phone(address)}"
        except MpesaError as error:
            messages.error(request, str(error))
            return redirect("wallet:request_withdrawal")
    elif network == "EAST_AFRICA":
        mobile_number = "".join(character for character in address if character.isdigit() or character == "+")
        if len(mobile_number.replace("+", "")) < 8 or len(mobile_number.replace("+", "")) > 15:
            messages.error(request, "Enter a valid East African mobile-money number.")
            return redirect("wallet:request_withdrawal")
        address = f"EAST-AFRICA:{mobile_number}"
    if amount <= 0:
        messages.error(request, "Enter a valid withdrawal amount.")
    elif amount < config.minimum_withdrawal:
        messages.error(request, f"Minimum withdrawal is {config.minimum_withdrawal:.2f} USDT.")
    elif amount > request.user.wallet.available_balance:
        messages.error(request, "Amount exceeds your withdrawable balance.")
    elif not address or not network:
        messages.error(request, "Enter both a withdrawal address and network.")
    elif network not in manual_payout_channels and not networks.filter(code=network).exists():
        messages.error(request, "Choose an available withdrawal network.")
    else:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            if amount > wallet.available_balance:
                messages.error(request, "Amount exceeds your withdrawable balance.")
                return redirect("wallet:request_withdrawal")
            before = wallet.available_balance
            wallet.available_balance -= amount
            wallet.save(update_fields=["available_balance", "updated_at"])
            request.user.withdrawal_address = address
            request.user.withdrawal_network = network
            request.user.save(update_fields=["withdrawal_address", "withdrawal_network"])
            withdrawal = WithdrawalRequest.objects.create(user=request.user, amount=amount, address=address, network=network)
            Transaction.objects.create(user=request.user, transaction_type=Transaction.TransactionType.WITHDRAWAL, amount=amount, balance_before=before, balance_after=wallet.available_balance, reference=f"WITHDRAWAL-REQUEST-{withdrawal.id}", description="Withdrawal amount reserved for manual processing", status=Transaction.Status.PENDING)
        messages.success(request, "Withdrawal request submitted. The amount is reserved from your withdrawable balance while it is reviewed.")
    return redirect("wallet:request_withdrawal")


@csrf_exempt
@require_POST
def crypto_webhook(request):
    """Signed provider webhook. Disabled unless a real provider mode and secret are configured."""
    secret = os.getenv("CRYPTO_PROVIDER_WEBHOOK_SECRET", "")
    if CRYPTO_PROVIDER_MODE == "mock" or not secret:
        return JsonResponse({"detail": "Webhook provider is not configured."}, status=503)
    signature = request.headers.get("X-Korex-Signature", "")
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return JsonResponse({"detail": "Invalid signature."}, status=401)
    try:
        event = json.loads(request.body)
        deposit, _ = record_provider_deposit(recipient_address=event["recipient_address"], transaction_hash=event["transaction_hash"], amount=event["amount"], asset=event["asset"], network=event["network"], status=event["status"], provider_reference=event.get("provider_reference"))
    except (KeyError, TypeError, ValueError) as error:
        return HttpResponseBadRequest(str(error))
    return JsonResponse({"deposit_id": deposit.id, "status": deposit.status})

@login_required
@require_POST
def mpesa_deposit(request):
    try:
        phone = normalize_phone(request.POST.get("phone_number", ""))
        usdt_amount, rate, amount_kes = quote_usdt_purchase(request.POST.get("amount_usdt", ""))
        response = initiate_stk_push(amount_kes, phone, request.user.account_id)
    except MpesaError as error:
        messages.error(request, str(error))
    else:
        deposit = MpesaDeposit.objects.create(user=request.user, amount_kes=amount_kes, amount_usdt=usdt_amount, rate_kes_per_usdt=rate, phone_number=phone, checkout_request_id=response["CheckoutRequestID"], merchant_request_id=response.get("MerchantRequestID", ""))
        transaction.on_commit(lambda: _alert_mpesa_prompt(deposit))
        messages.success(request, f"M-Pesa prompt sent for KES {amount_kes:,.0f}. Your {usdt_amount:,.2f} USDT quote is locked for this payment.")
        return redirect(f"/wallet/deposit/mpesa/?track={deposit.id}#mpesa-transactions")
    return redirect("wallet:mpesa_deposit")


@login_required
def mpesa_deposit_page(request):
    deposits = MpesaDeposit.objects.filter(user=request.user)[:15]
    return render(request, "wallet/mpesa_deposit.html", {"configured": mpesa_configured(), "deposits": deposits, "track_id": request.GET.get("track", ""), "is_production": settings.MPESA_ENVIRONMENT == "production"})


@login_required
def mpesa_deposit_status(request, deposit_id):
    deposit = MpesaDeposit.objects.filter(pk=deposit_id, user=request.user).first()
    if not deposit:
        return JsonResponse({"detail": "Not found."}, status=404)
    return JsonResponse({"id": deposit.pk, "status": deposit.status, "status_label": deposit.get_status_display(), "result_description": deposit.result_description, "final": deposit.status in {MpesaDeposit.Status.PAID, MpesaDeposit.Status.FAILED}})

@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        payload = json.loads(request.body)
        callback = payload["Body"]["stkCallback"]
        checkout_id = callback["CheckoutRequestID"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Malformed payment callback.")
    deposit = MpesaDeposit.objects.filter(checkout_request_id=checkout_id).first()
    if not deposit:
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
    result_code = int(callback.get("ResultCode", 1))
    metadata = {item.get("Name"): item.get("Value") for item in callback.get("CallbackMetadata", {}).get("Item", [])}
    paid_amount, paid_phone = metadata.get("Amount"), str(metadata.get("PhoneNumber", ""))
    try:
        valid_payment = result_code == 0 and paid_phone == deposit.phone_number and Decimal(str(paid_amount)).quantize(Decimal("0.01")) == deposit.amount_kes.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        valid_payment = False
    if valid_payment:
        try:
            provider_status = query_stk_status(deposit.checkout_request_id)
            valid_payment = provider_status.get("ResponseCode") == "0" and int(provider_status.get("ResultCode", 1)) == 0
        except (MpesaError, TypeError, ValueError):
            deposit.callback_payload = payload
            deposit.result_description = "Awaiting secure payment confirmation."
            deposit.save(update_fields=["callback_payload", "result_description", "updated_at"])
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
    deposit.result_code = result_code
    deposit.result_description = str(callback.get("ResultDesc", ""))[:255]
    deposit.callback_payload = payload
    deposit.receipt_number = str(metadata.get("MpesaReceiptNumber", ""))[:64]
    deposit.paid_amount_kes = paid_amount if valid_payment else None
    deposit.status = MpesaDeposit.Status.PAID if valid_payment else MpesaDeposit.Status.FAILED
    if not valid_payment and result_code == 0:
        deposit.result_description = "Payment details did not match the requested quote."
    deposit.save(update_fields=["result_code", "result_description", "callback_payload", "receipt_number", "paid_amount_kes", "status", "updated_at"])
    if valid_payment:
        transaction.on_commit(lambda: _alert_mpesa_confirmed(deposit))
    if valid_payment and settings.MPESA_AUTO_CREDIT_ENABLED:
        credit_confirmed_mpesa_deposit(deposit.id)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
