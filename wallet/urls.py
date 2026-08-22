from django.urls import path

from . import views

app_name = "wallet"
urlpatterns = [
    path("deposit/crypto/", views.deposit_crypto, name="deposit_crypto"),
    path("deposit/crypto/verify/", views.verify_transaction_hash, name="verify_transaction_hash"),
    path("webhooks/crypto/", views.crypto_webhook, name="crypto_webhook"),
]
