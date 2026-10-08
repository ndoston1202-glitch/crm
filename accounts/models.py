from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", _("Administrator")
        MANAGER = "manager", _("Menejer")
        OPERATOR = "operator", _("Operator")
        SERVICE = "service", _("Xizmat xodimi")

    role = models.CharField(_("Rol"), max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(_("Telefon"), max_length=20, blank=True)
    sip_extension = models.CharField(
        _("Ichki raqam (SIP)"), max_length=20, blank=True, db_index=True,
        help_text=_("Asterisk'dagi operator ichki raqami, masalan 101"),
    )

    api_token = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)

    @property
    def is_manager(self):
        return self.is_superuser or self.role in (self.Role.ADMIN, self.Role.MANAGER)

    @property
    def is_operator(self):
        return self.role == self.Role.OPERATOR

    @property
    def is_service(self):
        return self.role == self.Role.SERVICE

    def __str__(self):
        return self.get_full_name() or self.username
