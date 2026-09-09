from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("settings/", views.account_settings, name="account_settings"),
    path("two-factor/", views.two_factor_security, name="two_factor_security"),
    path("two-factor/setup/", views.two_factor_setup, name="two_factor_setup"),
    path("two-factor/verify/", views.two_factor_verify, name="two_factor_verify"),
    path("two-factor/recovery/", views.two_factor_recovery_login, name="two_factor_recovery_login"),
    path("two-factor/recovery-codes/", views.two_factor_recovery_codes, name="two_factor_recovery_codes"),
    path("two-factor/recovery-codes/new/", views.two_factor_regenerate_recovery_codes, name="two_factor_regenerate_recovery_codes"),
    path("two-factor/disable/", views.two_factor_disable, name="two_factor_disable"),
    path("kyc/", views.kyc, name="kyc"),
    path("kyc/start/", views.start_kyc, name="start_kyc"),
    path("kyc/done/", views.kyc_done, name="kyc_done"),
    path("api/webhooks/didit/", views.didit_webhook, name="didit_webhook"),
]
