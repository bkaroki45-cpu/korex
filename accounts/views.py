import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .email_verification import (
    TRUSTED_DEVICE_COOKIE, clear_trusted_device_cookie, create_trusted_device,
    issue_code, set_trusted_device_cookie, trusted_device_for_request, verify_code,
)
from .forms import EmailAuthenticationForm, EmailVerificationCodeForm, PasswordResetCodeForm, PasswordResetRequestForm, SignUpForm, WithdrawalDetailsForm
from .kyc import apply_webhook_event, create_didit_session, verification_for, verify_webhook_signature
from .models import EmailVerificationCode, TrustedDevice
from .security import clear_failures, is_locked, register_failure

PENDING_EMAIL_USER = "pending_email_verification_user_id"
PENDING_EMAIL_NEXT = "pending_email_verification_next"
PENDING_EMAIL_AT = "pending_email_verification_at"
PENDING_EMAIL_MAX_AGE_SECONDS = 900
RESEND_COOLDOWN = timedelta(minutes=10)
PENDING_RESET_USER = "pending_password_reset_user_id"
PENDING_RESET_AT = "pending_password_reset_at"
PENDING_TRUST_CHOICE = "pending_trust_device_choice"
PENDING_TRUST_NEXT = "pending_trust_device_next"


def _safe_next(request, value):
    return value if value and url_has_allowed_host_and_scheme(value, {request.get_host()}) else "dashboard"


def _set_pending_verification(request, user, destination):
    request.session.cycle_key()
    request.session[PENDING_EMAIL_USER] = user.pk
    request.session[PENDING_EMAIL_NEXT] = destination
    request.session[PENDING_EMAIL_AT] = timezone.now().timestamp()


def _pending_user(request):
    user_id, created_at = request.session.get(PENDING_EMAIL_USER), request.session.get(PENDING_EMAIL_AT)
    if not user_id or not created_at or timezone.now().timestamp() - created_at > PENDING_EMAIL_MAX_AGE_SECONDS:
        request.session.pop(PENDING_EMAIL_USER, None)
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True).first()


def _set_pending_reset(request, user):
    request.session.cycle_key()
    request.session[PENDING_RESET_USER] = user.pk
    request.session[PENDING_RESET_AT] = timezone.now().timestamp()


def _pending_reset_user(request):
    user_id, created_at = request.session.get(PENDING_RESET_USER), request.session.get(PENDING_RESET_AT)
    if not user_id or not created_at or timezone.now().timestamp() - created_at > PENDING_EMAIL_MAX_AGE_SECONDS:
        request.session.pop(PENDING_RESET_USER, None)
        request.session.pop(PENDING_RESET_AT, None)
        return None
    return get_user_model().objects.filter(pk=user_id, is_active=True).first()


def _code_context(user, purpose):
    latest = EmailVerificationCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).order_by("-created_at").first()
    expiry = latest.expires_at if latest else timezone.now() + RESEND_COOLDOWN
    return {"code_expires_at": expiry, "resend_available_at": expiry}


def _complete_email_login(request, user):
    destination = request.session.pop(PENDING_EMAIL_NEXT, "dashboard")
    request.session.pop(PENDING_EMAIL_USER, None)
    request.session.pop(PENDING_EMAIL_AT, None)
    login(request, user)
    request.session[PENDING_TRUST_CHOICE] = True
    request.session[PENDING_TRUST_NEXT] = destination
    return redirect("trust_device_prompt")


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
        _set_pending_verification(request, user, "dashboard")
        try:
            issue_code(user)
        except RuntimeError as error:
            form.add_error(None, str(error))
            return render(request, "accounts/signup.html", {"form": form})
        return redirect("email_verification")
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
            if trusted_device_for_request(user, request):
                login(request, user)
                return redirect(_safe_next(request, request.POST.get("next")))
            _set_pending_verification(request, user, _safe_next(request, request.POST.get("next")))
            try:
                issue_code(user)
            except RuntimeError as error:
                form.add_error(None, str(error))
                return render(request, "accounts/login.html", {"form": form})
            return redirect("email_verification")
        if request.method == "POST":
            register_failure(request, "password", email)
    return render(request, "accounts/login.html", {"form": form})


def email_verification(request):
    user = _pending_user(request)
    if not user:
        return redirect("login")
    form = EmailVerificationCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if is_locked(request, "email_code", user.pk):
            form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
        elif verify_code(user, form.cleaned_data["code"]):
            clear_failures(request, "email_code", user.pk)
            return _complete_email_login(request, user)
        else:
            register_failure(request, "email_code", user.pk)
            form.add_error("code", "That code is invalid, expired, or has already been used.")
    return render(request, "accounts/email_verification.html", {"form": form, "email": user.email, **_code_context(user, EmailVerificationCode.Purpose.LOGIN)})


@require_POST
def resend_email_verification(request):
    user = _pending_user(request)
    if not user:
        return redirect("login")
    latest = EmailVerificationCode.objects.filter(user=user, purpose=EmailVerificationCode.Purpose.LOGIN).order_by("-created_at").first()
    if latest and latest.created_at > timezone.now() - RESEND_COOLDOWN:
        messages.error(request, "Please wait until the 10-minute code timer finishes before requesting another code.")
    else:
        try:
            issue_code(user)
        except RuntimeError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "A new verification code has been sent. Your previous code no longer works.")
    return redirect("email_verification")


@login_required
def trust_device_prompt(request):
    """Ask the user before creating a persistent browser-trust credential."""
    if not request.session.get(PENDING_TRUST_CHOICE):
        return redirect("dashboard")
    if request.method == "POST":
        destination = request.session.pop(PENDING_TRUST_NEXT, "dashboard")
        request.session.pop(PENDING_TRUST_CHOICE, None)
        if request.POST.get("choice") == "yes":
            _, token = create_trusted_device(request.user, request)
            response = redirect(destination)
            set_trusted_device_cookie(response, token)
            messages.success(request, "This browser is trusted for 30 days. You can revoke it from Security at any time.")
            return response
        return redirect(destination)
    return render(request, "accounts/trust_device_prompt.html")


def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if user:
            _set_pending_reset(request, user)
            try:
                issue_code(user, EmailVerificationCode.Purpose.PASSWORD_RESET)
            except RuntimeError as error:
                form.add_error(None, str(error))
                return render(request, "accounts/password_reset_request.html", {"form": form})
            return redirect("password_reset_confirm")
        messages.success(request, "If that email belongs to an account, a reset code has been sent.")
        return redirect("login")
    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_confirm(request):
    user = _pending_reset_user(request)
    if not user:
        return redirect("password_reset_request")
    form = PasswordResetCodeForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        if is_locked(request, "password_reset_code", user.pk):
            form.add_error(None, "Too many attempts. Please wait 10 minutes before trying again.")
        elif verify_code(user, form.cleaned_data["code"], EmailVerificationCode.Purpose.PASSWORD_RESET):
            clear_failures(request, "password_reset_code", user.pk)
            form.save()
            request.session.pop(PENDING_RESET_USER, None)
            request.session.pop(PENDING_RESET_AT, None)
            messages.success(request, "Your password has been changed. Please sign in with your new password.")
            return redirect("login")
        else:
            register_failure(request, "password_reset_code", user.pk)
            form.add_error("code", "That code is invalid, expired, or has already been used.")
    return render(request, "accounts/password_reset_confirm.html", {"form": form, "email": user.email, **_code_context(user, EmailVerificationCode.Purpose.PASSWORD_RESET)})


@require_POST
def resend_password_reset_code(request):
    user = _pending_reset_user(request)
    if not user:
        return redirect("password_reset_request")
    latest = EmailVerificationCode.objects.filter(user=user, purpose=EmailVerificationCode.Purpose.PASSWORD_RESET).order_by("-created_at").first()
    if latest and latest.created_at > timezone.now() - RESEND_COOLDOWN:
        messages.error(request, "Please wait until the 10-minute code timer finishes before requesting another code.")
    else:
        try:
            issue_code(user, EmailVerificationCode.Purpose.PASSWORD_RESET)
        except RuntimeError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "A new reset code has been sent. Your previous code no longer works.")
    return redirect("password_reset_confirm")


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
    current_device = trusted_device_for_request(request.user, request)
    devices = request.user.trusted_devices.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())
    return render(request, "accounts/two_factor_security.html", {"devices": devices, "current_device": current_device})


@login_required
@require_POST
def revoke_trusted_device(request, device_id):
    device = get_object_or_404(TrustedDevice, pk=device_id, user=request.user, revoked_at__isnull=True)
    device.revoked_at = timezone.now()
    device.save(update_fields=["revoked_at"])
    response = redirect("two_factor_security")
    if trusted_device_for_request(request.user, request) and device.pk == trusted_device_for_request(request.user, request).pk:
        clear_trusted_device_cookie(response)
    return response


@login_required
@require_POST
def revoke_other_trusted_devices(request):
    current = trusted_device_for_request(request.user, request)
    devices = request.user.trusted_devices.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())
    if current:
        devices = devices.exclude(pk=current.pk)
    devices.update(revoked_at=timezone.now())
    messages.success(request, "All other trusted devices have been revoked.")
    return redirect("two_factor_security")


@login_required
def kyc(request):
    return render(request, "accounts/kyc.html", {"verification": verification_for(request.user)})


@login_required
@require_POST
def start_kyc(request):
    try:
        session = create_didit_session(user=request.user, callback_url=request.build_absolute_uri(reverse("kyc_done")))
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
