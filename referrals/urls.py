from django.urls import path

from .views import referrals_earnings

app_name = "referrals"
urlpatterns = [path("", referrals_earnings, name="overview")]
