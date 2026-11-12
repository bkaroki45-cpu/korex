from django.urls import path

from . import views

app_name = "support"
urlpatterns = [
    path("", views.support_request, name="request"),
    path("chat/<int:request_id>/", views.support_chat, name="chat"),
]
