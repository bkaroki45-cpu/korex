from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from .sitemaps import StaticViewSitemap
from .views import home, robots_txt
from accounts import views as account_views

admin.site.site_header = "CLOUDD 1 Administration"
admin.site.site_title = "CLOUDD 1 Admin"
admin.site.index_title = "Operations dashboard"


urlpatterns = [
    path("", home, name="home"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": {"static": StaticViewSitemap}}, name="sitemap"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("kyc/", account_views.kyc, name="kyc"),
    path("kyc/start/", account_views.start_kyc, name="start_kyc"),
    path("kyc/done/", account_views.kyc_done, name="kyc_done"),
    path("api/webhooks/didit/", account_views.didit_webhook, name="didit_webhook"),
    path("markets/", include("markets.urls")),
    path("referrals/", include("referrals.urls")),
    path("wallet/", include("wallet.urls")),

    path("dashboard/", include("dashboard.urls")),
    path("investments/", include("investments.urls")),
]
