import hashlib
import hmac
import json
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import CryptoDeposit
from .services import CRYPTO_PROVIDER_MODE, MINIMUM_USDT_DEPOSIT, get_deposit_address, record_provider_deposit, submit_transaction_hash


@login_required
def deposit_crypto(request):
    address = get_deposit_address(request.user)
    deposits = CryptoDeposit.objects.filter(user=request.user).select_related("deposit_address")[:15]
    return render(request, "wallet/deposit_crypto.html", {"address": address, "deposits": deposits, "minimum_deposit": MINIMUM_USDT_DEPOSIT, "mock_mode": CRYPTO_PROVIDER_MODE == "mock"})


@login_required
@require_POST
def verify_transaction_hash(request):
    txid = request.POST.get("transaction_hash", "").strip()
    if len(txid) < 20:
        messages.error(request, "Enter a valid transaction hash.")
    else:
        try:
            deposit = submit_transaction_hash(user=request.user, transaction_hash=txid)
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.info(request, f"Transaction submitted for verification. Status: {deposit.get_status_display()}.")
    return redirect("wallet:deposit_crypto")


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
