from django.urls import path

from . import views


app_name = "investments"


urlpatterns = [

    # Investments page
    path(
        "",
        views.investments,
        name="investments",
    ),

    # Create investment
    path(
        "create/<str:plan>/",
        views.create_investment,
        name="create_investment",
    ),

    # Earning sessions
    path(
        "<int:investment_id>/sessions/",
        views.earning_sessions,
        name="earning_sessions",
    ),
    path("signals/<int:signal_id>/participate/", views.participate, name="participate"),
]

