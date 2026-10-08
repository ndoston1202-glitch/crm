from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.poll, name="poll"),
    path("<int:pk>/", views.go, name="go"),
    path("read-all/", views.read_all, name="read_all"),
]
