"""Modullar ro'yxati va rollar bo'yicha standart ruxsatlar."""
from django.utils.translation import gettext_lazy as _

MODULES = [
    ("dashboard", _("Dashboard")),
    ("leads", _("Lidlar, voronka va qo'ng'iroqlar")),
    ("import", _("Lid import")),
    ("orders", _("Xizmat buyurtmalari")),
    ("reports", _("Analitika va hisobotlar")),
    ("phone_app", _("Telefon ilovasi")),
    ("hr", _("HR: xodimlar, davomat, ta'tillar")),
    ("users", _("Foydalanuvchilar va ruxsatlar")),
    ("settings", _("Sozlamalar (admin panel)")),
    ("update", _("Dasturni yangilash")),
]
MODULE_KEYS = [key for key, _label in MODULES]

# Faqat to'liq dostupli foydalanuvchi bera oladigan modullar (huquqni oshirib olishning oldini olish)
PRIVILEGED = {"users", "settings", "update"}

ROLE_DEFAULTS = {
    "admin": {"full_access": True, "modules": MODULE_KEYS, "data_scope": "all"},
    "manager": {
        "full_access": False,
        "modules": ["dashboard", "leads", "import", "orders", "reports", "phone_app", "hr"],
        "data_scope": "all",
    },
    "operator": {"full_access": False, "modules": ["dashboard", "leads", "phone_app"], "data_scope": "own"},
    "service": {"full_access": False, "modules": ["orders"], "data_scope": "own"},
}

# Bosh sahifa: ruxsat berilgan birinchi modul
HOME_ORDER = [
    ("dashboard", "crm:dashboard_page"),
    ("leads", "crm:my_work"),
    ("orders", "crm:order_list"),
    ("reports", "crm:reports"),
    ("hr", "hr:index"),
]
