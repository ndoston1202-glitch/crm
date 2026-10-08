from django.urls import path

from . import mobile_api, views

app_name = "telephony"

urlpatterns = [
    path("call/<int:lead_pk>/", views.click_to_call, name="click_to_call"),
    path("webhook/", views.webhook, name="webhook"),
    path("upload/", views.upload_recording, name="upload_recording"),
    path("poll/", views.poll, name="poll"),
    path("app/", views.mobile_app, name="mobile_app"),
    path("manual/<int:lead_pk>/", views.manual_upload, name="manual_upload"),
    path("mobile/login/", mobile_api.login, name="mobile_login"),
    path("mobile/me/", mobile_api.me, name="mobile_me"),
    path("mobile/logout/", mobile_api.logout, name="mobile_logout"),
    path("mobile/upload/", mobile_api.upload, name="mobile_upload"),
    path("recording/<int:pk>/", views.recording, name="recording"),
]
