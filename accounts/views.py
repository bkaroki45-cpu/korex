import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.db import transaction
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import EmailAuthenticationForm, SignUpForm, WithdrawalDetailsForm
from .kyc import apply_webhook_event, create_didit_session, verification_for, verify_webhook_signature


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None, initial={"referrer_code": request.GET.get("ref", "")})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
            referral_code = form.cleaned_data.get("referrer_code", "")
            if referral_code:
                from referrals.services import create_referral
                try:
                    create_referral(referred_user=user, referral_code=referral_code)
                except ValueError as error:
                    form.add_error("referrer_code", error)
                    transaction.set_rollback(True)
                    return render(request, "accounts/signup.html", {"form": form})
        login(request, user)
        return redirect("dashboard")
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = EmailAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.POST.get("next") or "dashboard")
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


@login_required
def account_settings(request):
    form = WithdrawalDetailsForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("account_settings")
    return render(request, "accounts/settings.html", {"form": form})


@login_required
def kyc(request):
    return render(request, "accounts/kyc.html", {"verification": verification_for(request.user)})


@login_required
@require_POST
def start_kyc(request):
    try:
        session = create_didit_session(
            user=request.user,
            callback_url=request.build_absolute_uri(reverse("kyc_done")),
        )
    except ValueError as error:
        return JsonResponse({"detail": str(error)}, status=503)
    return JsonResponse(session)


@login_required
def kyc_done(request):
    return render(request, "accounts/kyc_done.html", {"verification": verification_for(request.user)})


@csrf_exempt
@require_POST
def didit_webhook(request):
    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid JSON payload.")
    if not verify_webhook_signature(payload, request.headers.get("X-Signature-V2", ""), request.headers.get("X-Timestamp", "")):
        return JsonResponse({"detail": "Invalid webhook signature."}, status=401)
    if not apply_webhook_event(payload):
        return HttpResponseBadRequest("Unsupported or unmatched Didit event.")
    return JsonResponse({"ok": True})
