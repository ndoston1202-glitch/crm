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

    class Scope(models.TextChoices):
        ALL = "all", _("Barcha ma'lumotlar")
        OWN = "own", _("Faqat o'ziga tegishli")

    full_access = models.BooleanField(_("To'liq dostup"), default=False)
    modules = models.JSONField(_("Modullar"), default=list, blank=True)
    data_scope = models.CharField(_("Ma'lumotlar doirasi"), max_length=5, choices=Scope.choices, default=Scope.OWN)

    @property
    def has_full_access(self):
        return self.is_superuser or self.full_access

    def can(self, module):
        """Foydalanuvchi shu modulga kira oladimi."""
        return self.is_active and (self.has_full_access or module in (self.modules or []))

    @property
    def is_manager(self):
        """Barcha xodimlarning ma'lumotlarini ko'radi (aks holda faqat o'zinikini)."""
        return self.has_full_access or self.data_scope == self.Scope.ALL

    def save(self, *args, **kwargs):
        # Yangi foydalanuvchi: ruxsatlar aniq berilmagan bo'lsa, rol bo'yicha standart ruxsatlar
        if self._state.adding and not self.modules and not self.full_access and not getattr(self, "_explicit_access", False):
            self.apply_role_defaults()
        # Admin panel (Sozlamalar) faqat to'liq dostup yoki "settings" moduli bilan ochiladi
        self.is_staff = self.is_superuser or self.full_access or "settings" in (self.modules or [])
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if self.is_active and self.can("settings"):
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.can("settings"):
            return True
        return super().has_module_perms(app_label)

    def apply_role_defaults(self):
        from .permissions import ROLE_DEFAULTS

        defaults = ROLE_DEFAULTS.get(self.role, ROLE_DEFAULTS["operator"])
        self.full_access = defaults["full_access"]
        self.modules = list(defaults["modules"])
        self.data_scope = defaults["data_scope"]

    @property
    def is_operator(self):
        return self.role == self.Role.OPERATOR

    @property
    def is_service(self):
        return self.role == self.Role.SERVICE

    def __str__(self):
        return self.get_full_name() or self.username
