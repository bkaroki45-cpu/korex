from django.urls import path
from . import views
app_name = "wallet"
urlpatterns = [
    path("deposit/crypto/", views.deposit_crypto, name="deposit_crypto"),
    path("deposit/crypto/verify/", views.verify_transaction_hash, name="verify_transaction_hash"),
    path("deposit/mpesa/", views.mpesa_deposit_page, name="mpesa_deposit"),
    path("deposit/mpesa/start/", views.mpesa_deposit, name="mpesa_deposit_start"),
    path("withdraw/", views.request_withdrawal, name="request_withdrawal"),
    path("webhooks/crypto/", views.crypto_webhook, name="crypto_webhook"),
    path("webhooks/mpesa/", views.mpesa_callback, name="mpesa_callback"),
]