from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("settings/", views.account_settings, name="account_settings"),
    path("kyc/", views.kyc, name="kyc"),
    path("kyc/start/", views.start_kyc, name="start_kyc"),
    path("kyc/done/", views.kyc_done, name="kyc_done"),
    path("api/webhooks/didit/", views.didit_webhook, name="didit_webhook"),
]
