from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .models import Attendance, Employee, LeaveRequest

User = get_user_model()


class HrTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)
        self.op = User.objects.create_user("op", password="x", role=User.Role.OPERATOR)
        self.emp = Employee.objects.create(full_name="Vali Aliyev", user=self.op, work_start=time(9, 0))

    def test_clock_in_out(self):
        self.client.force_login(self.op)
        self.client.post(reverse("hr:clock"))
        rec = Attendance.objects.get(employee=self.emp)
        self.assertIsNotNone(rec.check_in)
        self.assertIsNone(rec.check_out)
        self.client.post(reverse("hr:clock"))
        rec.refresh_from_db()
        self.assertIsNotNone(rec.check_out)

    def test_late_minutes(self):
        day = timezone.localdate()
        tz = timezone.get_current_timezone()
        rec = Attendance(employee=self.emp, date=day, check_in=timezone.make_aware(datetime.combine(day, time(9, 25)), tz))
        self.assertEqual(rec.late_minutes, 25)
        rec.check_in = timezone.make_aware(datetime.combine(day, time(9, 5)), tz)
        self.assertEqual(rec.late_minutes, 0)  # 10 daqiqalik imtiyoz

    def test_leave_request_flow(self):
        self.client.force_login(self.op)
        self.client.post(reverse("hr:my"), {"kind": "vacation", "start_date": "2026-11-02", "end_date": "2026-11-06", "reason": "dam"})
        leave = LeaveRequest.objects.get()
        self.assertEqual(leave.days, 5)
        self.assertTrue(Notification.objects.filter(user=self.admin, kind="leave").exists())
        self.assertEqual(self.client.post(reverse("hr:leave_decide", args=[leave.pk]), {"decision": "approve"}).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(reverse("hr:leave_decide", args=[leave.pk]), {"decision": "approve"})
        leave.refresh_from_db()
        self.assertEqual((leave.status, leave.decided_by), ("approved", self.admin))
        self.assertTrue(Notification.objects.filter(user=self.op, kind="leave").exists())

    def test_hr_pages_and_employee_create(self):
        self.client.force_login(self.admin)
        for name in ["hr:index", "hr:employees", "hr:attendance", "hr:leaves", "hr:employee_create"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.client.post(reverse("hr:employee_create"), {
            "full_name": "Yangi Xodim", "new_department": "Call-markaz", "hire_date": "2026-10-01",
            "salary": "5000000", "work_start": "09:00", "work_end": "18:00", "status": "active",
        })
        e = Employee.objects.get(full_name="Yangi Xodim")
        self.assertEqual(e.department.name, "Call-markaz")

    def test_attendance_fix_and_report(self):
        self.client.force_login(self.admin)
        today = timezone.localdate()
        self.client.post(reverse("hr:attendance_fix"), {"employee": self.emp.pk, "date": today.isoformat(), "check_in": "09:30", "check_out": "18:00"})
        rec = Attendance.objects.get(employee=self.emp, date=today)
        self.assertEqual(rec.worked_display, "8:30")
        resp = self.client.get(reverse("hr:attendance"))
        row = next(r for r in resp.context["rows"] if r["e"] == self.emp)
        self.assertEqual((row["present"], row["late"]), (1, 1))
