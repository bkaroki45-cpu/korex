from django.urls import path

from .views import join_referral, referrals_earnings

app_name = "referrals"
urlpatterns = [
    path("", referrals_earnings, name="overview"),
    path("invite/<str:code>/", join_referral, name="join"),
]
