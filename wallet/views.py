import hashlib
import hmac
import json
import os
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import CryptoDeposit, PlatformConfiguration, WithdrawalNetwork, WithdrawalRequest, Wallet
from transactions.models import Transaction
from .services import CRYPTO_PROVIDER_MODE, get_deposit_address, record_provider_deposit, submit_manual_deposit
from accounts.kyc import is_kyc_verified


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
    if amount <= 0:
        messages.error(request, "Enter a valid withdrawal amount.")
    elif amount < config.minimum_withdrawal:
        messages.error(request, f"Minimum withdrawal is {config.minimum_withdrawal:.2f} USDT.")
    elif amount > request.user.wallet.available_balance:
        messages.error(request, "Amount exceeds your withdrawable balance.")
    elif not address or not network:
        messages.error(request, "Enter both a withdrawal address and network.")
    elif not networks.filter(code=network).exists():
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
