from django.contrib import admin

from .models import Attendance, Department, Employee, LeaveRequest

admin.site.register(Department)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department", "position", "status", "user")
    list_filter = ("status", "department")
    search_fields = ("full_name", "phone")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "check_in", "check_out")
    list_filter = ("date",)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "kind", "start_date", "end_date", "status")
    list_filter = ("status", "kind")
