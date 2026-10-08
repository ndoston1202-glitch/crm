from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Kind(models.TextChoices):
        CALLBACK = "callback", _("Qo'ng'iroq vaqti")
        LEAD = "lead", _("Yangi lid")
        ORDER = "order", _("Xizmat buyurtmasi")
        MISSED = "missed", _("O'tkazib yuborilgan qo'ng'iroq")
        UPDATE = "update", _("Yangilanish")

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=200)
    text = models.CharField(max_length=500, blank=True)
    url = models.CharField(max_length=300, blank=True)
    # Takrorlanmasligi uchun kalit: bir foydalanuvchiga bir xil hodisa ikki marta kelmaydi
    key = models.CharField(max_length=120, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "key"], condition=~models.Q(key=""), name="uniq_notification_key")
        ]
