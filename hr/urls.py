from django.urls import path

from . import views

app_name = "hr"

urlpatterns = [
    path("", views.index, name="index"),
    path("employees/", views.employees, name="employees"),
    path("employees/new/", views.employee_edit, name="employee_create"),
    path("employees/<int:pk>/", views.employee_edit, name="employee_edit"),
    path("attendance/", views.attendance, name="attendance"),
    path("attendance/fix/", views.attendance_fix, name="attendance_fix"),
    path("leaves/", views.leaves, name="leaves"),
    path("leaves/<int:pk>/decide/", views.leave_decide, name="leave_decide"),
    path("my/", views.my, name="my"),
    path("clock/", views.clock, name="clock"),
]
