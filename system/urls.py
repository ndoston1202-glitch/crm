from django.urls import path

from . import views

app_name = "system"

urlpatterns = [
    path("update/", views.update, name="update"),
    path("update/apply/", views.apply, name="apply"),
    path("ping/", views.ping, name="ping"),
]
