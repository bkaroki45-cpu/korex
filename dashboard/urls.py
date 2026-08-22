from django.urls import path

from .views import dashboard, wallet_action


urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("wallet/<str:action>/", wallet_action, name="wallet_action"),
]
