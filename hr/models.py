from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

LATE_GRACE_MINUTES = 10


class Department(models.Model):
    name = models.CharField(_("Nomi"), max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Bo'lim")
        verbose_name_plural = _("Bo'limlar")

    def __str__(self):
        return self.name


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Ishlayapti")
        DISMISSED = "dismissed", _("Ishdan ketgan")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name=_("CRM foydalanuvchisi"), on_delete=models.SET_NULL,
        null=True, blank=True, related_name="employee",
    )
    full_name = models.CharField(_("F.I.Sh."), max_length=200)
    phone = models.CharField(_("Telefon"), max_length=20, blank=True)
    department = models.ForeignKey(Department, verbose_name=_("Bo'lim"), on_delete=models.SET_NULL, null=True, blank=True)
    position = models.CharField(_("Lavozim"), max_length=120, blank=True)
    hire_date = models.DateField(_("Ishga kirgan sana"), default=timezone.localdate)
    birth_date = models.DateField(_("Tug'ilgan sana"), null=True, blank=True)
    salary = models.DecimalField(_("Oylik maosh"), max_digits=14, decimal_places=0, default=0)
    work_start = models.TimeField(_("Ish boshlanishi"), default=time(9, 0))
    work_end = models.TimeField(_("Ish tugashi"), default=time(18, 0))
    status = models.CharField(_("Holat"), max_length=10, choices=Status.choices, default=Status.ACTIVE)
    dismissed_at = models.DateField(_("Ishdan ketgan sana"), null=True, blank=True)
    notes = models.TextField(_("Izoh"), blank=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = _("Xodim")
        verbose_name_plural = _("Xodimlar")

    def __str__(self):
        return self.full_name


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField(_("Sana"), default=timezone.localdate, db_index=True)
    check_in = models.DateTimeField(_("Keldi"), null=True, blank=True)
    check_out = models.DateTimeField(_("Ketdi"), null=True, blank=True)
    note = models.CharField(_("Izoh"), max_length=255, blank=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("employee", "date")]
        verbose_name = _("Davomat")
        verbose_name_plural = _("Davomat")

    @property
    def late_minutes(self):
        if not self.check_in:
            return 0
        start = timezone.make_aware(datetime.combine(self.date, self.employee.work_start))
        delta = (self.check_in - start).total_seconds() / 60
        return int(delta) if delta > LATE_GRACE_MINUTES else 0

    @property
    def worked(self):
        if self.check_in and self.check_out and self.check_out > self.check_in:
            return self.check_out - self.check_in
        return timedelta(0)

    @property
    def worked_display(self):
        minutes = int(self.worked.total_seconds() // 60)
        return f"{minutes // 60}:{minutes % 60:02d}" if minutes else "—"


class LeaveRequest(models.Model):
    class Kind(models.TextChoices):
        VACATION = "vacation", _("Mehnat ta'tili")
        SICK = "sick", _("Kasallik")
        UNPAID = "unpaid", _("O'z hisobidan")
        OTHER = "other", _("Boshqa")

    class Status(models.TextChoices):
        PENDING = "pending", _("Ko'rib chiqilmoqda")
        APPROVED = "approved", _("Tasdiqlandi")
        REJECTED = "rejected", _("Rad etildi")

    employee = models.ForeignKey(Employee, verbose_name=_("Xodim"), on_delete=models.CASCADE, related_name="leaves")
    kind = models.CharField(_("Turi"), max_length=10, choices=Kind.choices, default=Kind.VACATION)
    start_date = models.DateField(_("Boshlanishi"))
    end_date = models.DateField(_("Tugashi"))
    reason = models.TextField(_("Sabab"), blank=True)
    status = models.CharField(_("Holat"), max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Ta'til so'rovi")
        verbose_name_plural = _("Ta'til so'rovlari")

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1
