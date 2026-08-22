from django.urls import path
from .views import markets

app_name = "markets"
urlpatterns = [path("", markets, name="markets")]
