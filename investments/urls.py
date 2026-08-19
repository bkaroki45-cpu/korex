from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.investments,
        name="investments",
    ),

    path(
        "create/<str:plan>/",
        views.create_investment,
        name="create_investment",
    ),

    path(
        "<int:investment_id>/sessions/",
        views.earning_sessions,
        name="earning_sessions",
    ),
]