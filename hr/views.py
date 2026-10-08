import calendar
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from crm.views import module_required
from notifications.services import notify

from .forms import AttendanceFixForm, EmployeeForm, LeaveRequestForm
from .models import Attendance, Employee, LeaveRequest


def hr_users():
    from django.contrib.auth import get_user_model

    return [u for u in get_user_model().objects.filter(is_active=True) if u.can("hr")]


def _month(request):
    today = timezone.localdate()
    try:
        y, m = map(int, request.GET.get("month", "").split("-"))
        first = date(y, m, 1)
    except ValueError:
        first = today.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return first, min(last, today) if first <= today else last, last


def _on_leave(day):
    return LeaveRequest.objects.filter(status=LeaveRequest.Status.APPROVED, start_date__lte=day, end_date__gte=day)


@module_required("hr")
def index(request):
    today = timezone.localdate()
    active = Employee.objects.filter(status=Employee.Status.ACTIVE).select_related("department")
    records = {a.employee_id: a for a in Attendance.objects.filter(date=today).select_related("employee")}
    on_leave = set(_on_leave(today).values_list("employee_id", flat=True))
    rows = []
    for e in active:
        a = records.get(e.pk)
        state = "leave" if e.pk in on_leave else ("late" if a and a.late_minutes else ("present" if a and a.check_in else "absent"))
        rows.append({"e": e, "a": a, "state": state})
    birthdays = [e for e in active if e.birth_date and e.birth_date.month == today.month]
    return render(request, "hr/index.html", {
        "rows": rows,
        "total": len(rows),
        "present": sum(r["state"] in ("present", "late") for r in rows),
        "late": sum(r["state"] == "late" for r in rows),
        "leave": sum(r["state"] == "leave" for r in rows),
        "pending": LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count(),
        "birthdays": sorted(birthdays, key=lambda e: e.birth_date.day),
        "fix_form": AttendanceFixForm(initial={"date": today}),
    })


@module_required("hr")
def employees(request):
    status = request.GET.get("status", Employee.Status.ACTIVE)
    qs = Employee.objects.select_related("department", "user")
    if status:
        qs = qs.filter(status=status)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(position__icontains=q))
    return render(request, "hr/employees.html", {"employees": qs, "status": status, "q": q, "statuses": Employee.Status.choices})


@module_required("hr")
def employee_edit(request, pk=None):
    obj = get_object_or_404(Employee, pk=pk) if pk else Employee()
    form = EmployeeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saqlandi"))
        return redirect("hr:employees")
    leaves = obj.leaves.all()[:10] if pk else []
    return render(request, "hr/employee_form.html", {"form": form, "obj": obj if pk else None, "leaves": leaves})


@module_required("hr")
def attendance(request):
    first, until, last = _month(request)
    employees_qs = Employee.objects.filter(Q(status=Employee.Status.ACTIVE) | Q(dismissed_at__gte=first)).select_related("department")
    records = Attendance.objects.filter(date__range=(first, last)).select_related("employee")
    by_emp = {}
    for a in records:
        by_emp.setdefault(a.employee_id, []).append(a)
    leaves = LeaveRequest.objects.filter(status=LeaveRequest.Status.APPROVED, start_date__lte=last, end_date__gte=first)
    workdays = sum(1 for i in range((until - first).days + 1) if (first + timedelta(i)).weekday() < 6) if until >= first else 0
    rows = []
    for e in employees_qs:
        recs = by_emp.get(e.pk, [])
        leave_days = sum(
            1 for lv in leaves if lv.employee_id == e.pk
            for i in range((min(lv.end_date, until) - max(lv.start_date, first)).days + 1)
            if (max(lv.start_date, first) + timedelta(i)).weekday() < 6
        )
        present = sum(1 for a in recs if a.check_in)
        worked = sum((a.worked for a in recs), timedelta())
        minutes = int(worked.total_seconds() // 60)
        rows.append({
            "e": e, "present": present, "late": sum(1 for a in recs if a.late_minutes), "leave": leave_days,
            "absent": max(workdays - present - leave_days, 0), "hours": f"{minutes // 60}:{minutes % 60:02d}",
        })
    return render(request, "hr/attendance.html", {
        "rows": rows, "month": first, "workdays": workdays,
        "prev": (first - timedelta(days=1)).strftime("%Y-%m"), "next": (last + timedelta(days=1)).strftime("%Y-%m"),
    })


@module_required("hr")
@require_POST
def attendance_fix(request):
    form = AttendanceFixForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        rec, _created = Attendance.objects.get_or_create(employee=d["employee"], date=d["date"])
        tz = timezone.get_current_timezone()
        rec.check_in = timezone.make_aware(datetime.combine(d["date"], d["check_in"]), tz) if d["check_in"] else None
        rec.check_out = timezone.make_aware(datetime.combine(d["date"], d["check_out"]), tz) if d["check_out"] else None
        rec.note = _("HR tomonidan to'g'irlandi: %(u)s") % {"u": request.user}
        rec.save()
        messages.success(request, _("Davomat saqlandi"))
    else:
        messages.error(request, _("Formada xatolik bor"))
    return redirect("hr:index")


@module_required("hr")
def leaves(request):
    status = request.GET.get("status", LeaveRequest.Status.PENDING)
    qs = LeaveRequest.objects.select_related("employee", "decided_by")
    if status:
        qs = qs.filter(status=status)
    return render(request, "hr/leaves.html", {"leaves": qs, "status": status, "statuses": LeaveRequest.Status.choices})


@module_required("hr")
@require_POST
def leave_decide(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, status=LeaveRequest.Status.PENDING)
    approve = request.POST.get("decision") == "approve"
    leave.status = LeaveRequest.Status.APPROVED if approve else LeaveRequest.Status.REJECTED
    leave.decided_by = request.user
    leave.decided_at = timezone.now()
    leave.save()
    if leave.employee.user:
        notify(
            leave.employee.user, "leave",
            (_("Ta'til so'rovingiz tasdiqlandi") if approve else _("Ta'til so'rovingiz rad etildi")),
            text=f"{leave.start_date:%d.%m} – {leave.end_date:%d.%m}", url=reverse("hr:my"),
        )
    messages.success(request, _("Tasdiqlandi") if approve else _("Rad etildi"))
    return redirect("hr:leaves")


# ---------- Xodimning o'zi uchun ----------
def _my_employee(request):
    employee = getattr(request.user, "employee", None)
    if employee is None:
        raise Http404
    return employee


@login_required
def my(request):
    employee = getattr(request.user, "employee", None)
    if employee is None:
        return render(request, "hr/my.html", {"employee": None})
    first = timezone.localdate().replace(day=1)
    form = LeaveRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        leave = form.save(commit=False)
        leave.employee = employee
        leave.save()
        notify(hr_users(), "leave", _("Yangi ta'til so'rovi: %(n)s") % {"n": employee.full_name},
               text=f"{leave.get_kind_display()} · {leave.start_date:%d.%m} – {leave.end_date:%d.%m}",
               url=reverse("hr:leaves"))
        messages.success(request, _("So'rov yuborildi"))
        return redirect("hr:my")
    return render(request, "hr/my.html", {
        "employee": employee,
        "today": Attendance.objects.filter(employee=employee, date=timezone.localdate()).first(),
        "records": employee.attendance.filter(date__gte=first),
        "leaves": employee.leaves.all()[:10],
        "form": form,
    })


@login_required
@require_POST
def clock(request):
    employee = _my_employee(request)
    rec, _created = Attendance.objects.get_or_create(employee=employee, date=timezone.localdate())
    now = timezone.now()
    if rec.check_in is None:
        rec.check_in = now
        msg = _("Ishga kelganingiz belgilandi: %(t)s") % {"t": timezone.localtime(now).strftime("%H:%M")}
    else:
        rec.check_out = now
        msg = _("Ketganingiz belgilandi: %(t)s") % {"t": timezone.localtime(now).strftime("%H:%M")}
    rec.save()
    messages.success(request, msg)
    return redirect(request.POST.get("next") or "hr:my")
