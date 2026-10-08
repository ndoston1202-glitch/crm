from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("Yangi")
        IN_PROGRESS = "in_progress", _("Ishlanmoqda")
        CALLBACK = "callback", _("Qayta qo'ng'iroq")
        INTERESTED = "interested", _("Qiziqdi")
        WON = "won", _("Sotuv")
        LOST = "lost", _("Rad etildi")

    class Source(models.TextChoices):
        WEBSITE = "website", _("Sayt")
        INSTAGRAM = "instagram", _("Instagram")
        TELEGRAM = "telegram", _("Telegram")
        FACEBOOK = "facebook", _("Facebook")
        CALL = "call", _("Kiruvchi qo'ng'iroq")
        REFERRAL = "referral", _("Tavsiya")
        OTHER = "other", _("Boshqa")

    full_name = models.CharField(_("F.I.Sh."), max_length=200)
    phone = models.CharField(_("Telefon"), max_length=20, db_index=True)
    extra_phone = models.CharField(_("Qo'shimcha telefon"), max_length=20, blank=True)
    region = models.CharField(_("Hudud"), max_length=100, blank=True)
    source = models.CharField(_("Manba"), max_length=20, choices=Source.choices, default=Source.OTHER)
    status = models.CharField(_("Holat"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Operator"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        limit_choices_to={"role": "operator"},
    )
    next_call_at = models.DateTimeField(_("Keyingi qo'ng'iroq"), null=True, blank=True)
    comment = models.TextField(_("Izoh"), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(_("Yaratilgan"), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Lid")
        verbose_name_plural = _("Lidlar")

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class Call(models.Model):
    class Result(models.TextChoices):
        ANSWERED = "answered", _("Gaplashildi")
        NO_ANSWER = "no_answer", _("Javob bermadi")
        BUSY = "busy", _("Band")
        WRONG_NUMBER = "wrong_number", _("Noto'g'ri raqam")
        CALLBACK = "callback", _("Qayta qo'ng'iroq so'radi")

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="calls")
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Operator"), on_delete=models.SET_NULL, null=True, related_name="calls"
    )
    result = models.CharField(_("Natija"), max_length=20, choices=Result.choices)
    note = models.TextField(_("Izoh"), blank=True)
    created_at = models.DateTimeField(_("Vaqt"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Qo'ng'iroq")
        verbose_name_plural = _("Qo'ng'iroqlar")


class Service(models.Model):
    name = models.CharField(_("Nomi"), max_length=200)
    price = models.DecimalField(_("Narxi"), max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(_("Faol"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Xizmat")
        verbose_name_plural = _("Xizmatlar")

    def __str__(self):
        return self.name


class Sale(models.Model):
    lead = models.ForeignKey(Lead, verbose_name=_("Lid"), on_delete=models.PROTECT, related_name="sales")
    service = models.ForeignKey(Service, verbose_name=_("Xizmat"), on_delete=models.PROTECT, related_name="sales")
    amount = models.DecimalField(_("Summa"), max_digits=14, decimal_places=2)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("Operator"), on_delete=models.SET_NULL, null=True, related_name="sales"
    )
    note = models.TextField(_("Izoh"), blank=True)
    created_at = models.DateTimeField(_("Sana"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Sotuv")
        verbose_name_plural = _("Sotuvlar")

    def __str__(self):
        return f"#{self.pk} {self.lead.full_name} — {self.service}"


class ServiceOrder(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("Yangi")
        IN_PROGRESS = "in_progress", _("Bajarilmoqda")
        DONE = "done", _("Bajarildi")
        CANCELLED = "cancelled", _("Bekor qilindi")

    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name="order")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Mas'ul xodim"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_orders",
        limit_choices_to={"role": "service"},
    )
    status = models.CharField(_("Holat"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    scheduled_at = models.DateTimeField(_("Rejalashtirilgan vaqt"), null=True, blank=True)
    address = models.CharField(_("Manzil"), max_length=255, blank=True)
    note = models.TextField(_("Izoh"), blank=True)
    completed_at = models.DateTimeField(_("Bajarilgan vaqt"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Xizmat buyurtmasi")
        verbose_name_plural = _("Xizmat buyurtmalari")

    def __str__(self):
        return f"#{self.pk} {self.sale.lead.full_name}"
