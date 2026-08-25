from django.contrib import admin
from django.urls import include, path

from .views import home

admin.site.site_header = "CLOUDD 1 Administration"
admin.site.site_title = "CLOUDD 1 Admin"
admin.site.index_title = "Operations dashboard"


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("markets/", include("markets.urls")),
    path("referrals/", include("referrals.urls")),
    path("wallet/", include("wallet.urls")),

    path("dashboard/", include("dashboard.urls")),
    path("investments/", include("investments.urls")),
]
