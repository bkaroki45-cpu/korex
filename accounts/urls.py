from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-reset/resend/", views.resend_password_reset_code, name="resend_password_reset_code"),
    path("logout/", views.logout_view, name="logout"),
    path("settings/", views.account_settings, name="account_settings"),
    path("two-factor/", views.two_factor_security, name="two_factor_security"),
    path("verify-email/", views.email_verification, name="email_verification"),
    path("verify-email/resend/", views.resend_email_verification, name="resend_email_verification"),
    path("two-factor/devices/<int:device_id>/revoke/", views.revoke_trusted_device, name="revoke_trusted_device"),
    path("two-factor/devices/revoke-others/", views.revoke_other_trusted_devices, name="revoke_other_trusted_devices"),
    path("kyc/", views.kyc, name="kyc"),
    path("kyc/start/", views.start_kyc, name="start_kyc"),
    path("kyc/done/", views.kyc_done, name="kyc_done"),
    path("api/webhooks/didit/", views.didit_webhook, name="didit_webhook"),
]
