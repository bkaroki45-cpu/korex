from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db import transaction

from .forms import EmailAuthenticationForm, SignUpForm, WithdrawalDetailsForm


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
