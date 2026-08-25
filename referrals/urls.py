from django.urls import path

from .views import join_referral, referrals_earnings

app_name = "referrals"
urlpatterns = [
    path("", referrals_earnings, name="overview"),
    path("referral/<str:code>/", join_referral, name="join"),
    # Keep previously shared links working while all newly generated links use
    # the clearer /referral/ URL.
    path("invite/<str:code>/", join_referral, name="legacy_join"),
]
