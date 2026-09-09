import json

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import DisableTwoFactorForm, EmailAuthenticationForm, RecoveryCodeForm, SignUpForm, TotpCodeForm, WithdrawalDetailsForm
from .kyc import apply_webhook_event, create_didit_session, verification_for, verify_webhook_signature
from .models import TwoFactorSettings
from .security import clear_failures, is_locked, register_failure
from .totp import decrypt_secret, encrypt_secret, generate_recovery_codes, generate_secret, use_recovery_code, verify_totp

PENDING_2FA_USER = "pending_two_factor_user_id"
PENDING_2FA_NEXT = "pending_two_factor_next"
PENDING_2FA_AT = "pending_two_factor_at"
PENDING_2FA_MAX_AGE_SECONDS = 300


def _safe_next(request, value):
    return value if value and url_has_allowed_host_and_scheme(value, {request.get_host()}) else "dashboard"


def _pending_user(request):
    user_id, created_at = request.session.get(PENDING_2FA_USER), request.session.get(PENDING_2FA_AT)
    if not user_id or not created_at or timezone.now().timestamp() - created_at > PENDING_2FA_MAX_AGE_SECONDS:
        request.session.pop(PENDING_2FA_USER, None)
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True).first()


def _finish_two_factor_login(request, user):
    destination = request.session.pop(PENDING_2FA_NEXT, "dashboard")
    request.session.pop(PENDING_2FA_USER, None)
    request.session.pop(PENDING_2FA_AT, None)
    login(request, user)
    return redirect(destination)


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
    email = request.POST.get("username", "")
    if request.method == "POST" and is_locked(request, "password", email):
        form = EmailAuthenticationForm(request, data=request.POST)
        form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
    else:
        form = EmailAuthenticationForm(request, data=request.POST or None)
        if request.method == "POST" and form.is_valid():
            user = form.get_user()
            clear_failures(request, "password", email)
            two_factor = getattr(user, "two_factor", None)
            if two_factor and two_factor.is_enabled:
                request.session.cycle_key()
                request.session[PENDING_2FA_USER] = user.pk
                request.session[PENDING_2FA_NEXT] = _safe_next(request, request.POST.get("next"))
                request.session[PENDING_2FA_AT] = timezone.now().timestamp()
                return redirect("two_factor_verify")
            login(request, user)
            return redirect(_safe_next(request, request.POST.get("next")))
        if request.method == "POST":
            register_failure(request, "password", email)
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
def two_factor_security(request):
    two_factor, _ = TwoFactorSettings.objects.get_or_create(user=request.user)
    remaining_codes = two_factor.recovery_codes.filter(used_at__isnull=True).count()
    return render(request, "accounts/two_factor_security.html", {"two_factor": two_factor, "remaining_codes": remaining_codes})


@login_required
def two_factor_setup(request):
    two_factor, _ = TwoFactorSettings.objects.get_or_create(user=request.user)
    reenrollment = request.session.get("two_factor_reenroll_required", False)
    needs_existing_authenticator = two_factor.is_enabled and not reenrollment
    if needs_existing_authenticator and not request.session.get("two_factor_change_authorized"):
        form = TotpCodeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            if is_locked(request, "change_totp", request.user.pk):
                form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
            elif verify_totp(decrypt_secret(two_factor.encrypted_secret), form.cleaned_data["code"]):
                clear_failures(request, "change_totp", request.user.pk)
                request.session["two_factor_change_authorized"] = True
                return redirect("two_factor_setup")
            else:
                register_failure(request, "change_totp", request.user.pk)
                form.add_error("code", "That authenticator code is not valid.")
        return render(request, "accounts/two_factor_authorize.html", {"form": form, "reenrollment": False})

    secret = request.session.get("two_factor_enrollment_secret")
    if not secret:
        secret = generate_secret()
        request.session["two_factor_enrollment_secret"] = secret
    form = TotpCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if is_locked(request, "setup_totp", request.user.pk):
            form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
        elif verify_totp(secret, form.cleaned_data["code"]):
            clear_failures(request, "setup_totp", request.user.pk)
            two_factor.encrypted_secret = encrypt_secret(secret)
            two_factor.is_enabled = True
            two_factor.enabled_at = timezone.now()
            two_factor.save(update_fields=["encrypted_secret", "is_enabled", "enabled_at", "updated_at"])
            recovery_codes = generate_recovery_codes(two_factor)
            request.session.pop("two_factor_enrollment_secret", None)
            request.session.pop("two_factor_change_authorized", None)
            request.session.pop("two_factor_reenroll_required", None)
            request.session["new_recovery_codes"] = recovery_codes
            return redirect("two_factor_recovery_codes")
        else:
            register_failure(request, "setup_totp", request.user.pk)
            form.add_error("code", "That authenticator code is not valid. Try the current code and check your device time.")
    return render(request, "accounts/two_factor_setup.html", {"form": form, "secret": secret, "reenrollment": reenrollment})


def two_factor_verify(request):
    user = _pending_user(request)
    if not user:
        return redirect("login")
    two_factor = getattr(user, "two_factor", None)
    if not two_factor or not two_factor.is_enabled:
        return redirect("login")
    if is_locked(request, "totp", user.pk):
        form = TotpCodeForm()
        form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
    else:
        form = TotpCodeForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            if verify_totp(decrypt_secret(two_factor.encrypted_secret), form.cleaned_data["code"]):
                clear_failures(request, "totp", user.pk)
                return _finish_two_factor_login(request, user)
            register_failure(request, "totp", user.pk)
            form.add_error("code", "That authenticator code is not valid.")
    return render(request, "accounts/two_factor_verify.html", {"form": form})


def two_factor_recovery_login(request):
    user = _pending_user(request)
    if not user:
        return redirect("login")
    two_factor = getattr(user, "two_factor", None)
    form = RecoveryCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if is_locked(request, "recovery", user.pk):
            form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
        elif two_factor and use_recovery_code(two_factor, form.cleaned_data["code"]):
            clear_failures(request, "recovery", user.pk)
            request.session["two_factor_reenroll_required"] = True
            _finish_two_factor_login(request, user)
            return redirect("two_factor_setup")
        else:
            register_failure(request, "recovery", user.pk)
            form.add_error("code", "That recovery code is not valid or has already been used.")
    return render(request, "accounts/two_factor_recovery_login.html", {"form": form})


@login_required
def two_factor_recovery_codes(request):
    codes = request.session.pop("new_recovery_codes", None)
    if not codes:
        return redirect("two_factor_security")
    return render(request, "accounts/two_factor_recovery_codes.html", {"codes": codes})


@login_required
@require_POST
def two_factor_regenerate_recovery_codes(request):
    two_factor, _ = TwoFactorSettings.objects.get_or_create(user=request.user)
    form = TotpCodeForm(request.POST)
    if not two_factor.is_enabled or not form.is_valid() or not verify_totp(decrypt_secret(two_factor.encrypted_secret), form.cleaned_data["code"]):
        messages.error(request, "Enter a valid current authenticator code to generate new recovery codes.")
        return redirect("two_factor_security")
    request.session["new_recovery_codes"] = generate_recovery_codes(two_factor)
    return redirect("two_factor_recovery_codes")


@login_required
@require_POST
def two_factor_disable(request):
    two_factor, _ = TwoFactorSettings.objects.get_or_create(user=request.user)
    form = DisableTwoFactorForm(request.POST)
    if not two_factor.is_enabled or not form.is_valid() or not request.user.check_password(form.cleaned_data["password"]) or not verify_totp(decrypt_secret(two_factor.encrypted_secret), form.cleaned_data["code"]):
        messages.error(request, "2FA was not disabled. Enter your password and a valid current authenticator code.")
        return redirect("two_factor_security")
    two_factor.recovery_codes.all().delete()
    two_factor.encrypted_secret, two_factor.is_enabled, two_factor.enabled_at = "", False, None
    two_factor.save(update_fields=["encrypted_secret", "is_enabled", "enabled_at", "updated_at"])
    messages.success(request, "Two-factor authentication has been disabled.")
    return redirect("two_factor_security")


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
