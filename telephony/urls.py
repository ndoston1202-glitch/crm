from django.urls import path

from . import views

app_name = "telephony"

urlpatterns = [
    path("call/<int:lead_pk>/", views.click_to_call, name="click_to_call"),
    path("webhook/", views.webhook, name="webhook"),
    path("upload/", views.upload_recording, name="upload_recording"),
    path("poll/", views.poll, name="poll"),
    path("recording/<int:pk>/", views.recording, name="recording"),
]
