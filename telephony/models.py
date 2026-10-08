from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PhoneCall(models.Model):
    class Direction(models.TextChoices):
        INCOMING = "in", _("Kiruvchi")
        OUTGOING = "out", _("Chiquvchi")

    class Status(models.TextChoices):
        RINGING = "ringing", _("Jiringlamoqda")
        ANSWERED = "answered", _("Javob berildi")
        NO_ANSWER = "no_answer", _("Javobsiz")
        BUSY = "busy", _("Band")
        FAILED = "failed", _("Xatolik")

    class Source(models.TextChoices):
        ASTERISK = "asterisk", _("ATS")
        MOBILE = "mobile", _("Telefon ilovasi")
        MANUAL = "manual", _("Qo'lda yuklangan")

    uniqueid = models.CharField(max_length=64, blank=True, db_index=True)
    source = models.CharField(_("Manba"), max_length=10, choices=Source.choices, default=Source.ASTERISK)
    # Telefon ilovasi yuborgan fayl identifikatori — bir yozuv ikki marta yuklanmasligi uchun
    client_id = models.CharField(max_length=120, null=True, blank=True, unique=True)
    direction = models.CharField(_("Yo'nalish"), max_length=3, choices=Direction.choices)
    status = models.CharField(_("Holat"), max_length=20, choices=Status.choices, default=Status.RINGING, db_index=True)
    phone = models.CharField(_("Mijoz raqami"), max_length=32)
    extension = models.CharField(_("Ichki raqam"), max_length=20, blank=True)
    lead = models.ForeignKey("crm.Lead", on_delete=models.SET_NULL, null=True, blank=True, related_name="phone_calls")
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Operator"), on_delete=models.SET_NULL, null=True, blank=True,
        related_name="phone_calls",
    )
    started_at = models.DateTimeField(_("Boshlangan"), auto_now_add=True, db_index=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(_("Davomiylik (s)"), default=0)
    recording = models.FileField(_("Ovoz yozuvi"), upload_to="recordings/%Y/%m/", blank=True)
    transcript = models.TextField(_("Suhbat matni"), blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = _("Telefon qo'ng'irog'i")
        verbose_name_plural = _("Telefon qo'ng'iroqlari")

    def __str__(self):
        return f"{self.get_direction_display()} {self.phone} {self.started_at:%d.%m %H:%M}"

    @property
    def duration_display(self):
        return f"{self.duration // 60}:{self.duration % 60:02d}"
