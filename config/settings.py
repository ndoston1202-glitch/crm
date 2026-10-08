import os
import sys
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# .env faylidan sozlamalarni o'qish (o'rnatuvchi yaratadi): KALIT=qiymat
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _key, _sep, _value = _line.strip().partition("=")
        if _sep and not _key.startswith("#"):
            os.environ.setdefault(_key.strip(), _value.strip())

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "crm",
    "telephony",
    "notifications",
    "system",
    "hr",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL agar POSTGRES_DB berilgan bo'lsa, aks holda SQLite (lokal ishlab chiqish uchun)
if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "crm:dashboard"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "uz"
LANGUAGES = [("uz", _("O'zbekcha")), ("ru", _("Ruscha"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Asterisk IP-telefoniya ---
ASTERISK = {
    # AMI (bir bosishda qo'ng'iroq uchun). manager.conf dagi foydalanuvchi.
    "AMI_HOST": os.environ.get("ASTERISK_AMI_HOST", ""),
    "AMI_PORT": int(os.environ.get("ASTERISK_AMI_PORT", "5038")),
    "AMI_USER": os.environ.get("ASTERISK_AMI_USER", "crm"),
    "AMI_SECRET": os.environ.get("ASTERISK_AMI_SECRET", ""),
    "AMI_TIMEOUT": 5,
    # Operator telefonini chaqirish kanali: PJSIP/{extension} yoki SIP/{extension}
    "CHANNEL_TEMPLATE": os.environ.get("ASTERISK_CHANNEL_TEMPLATE", "PJSIP/{extension}"),
    # Tashqi raqamga chiqish konteksti (extensions.conf)
    "OUTBOUND_CONTEXT": os.environ.get("ASTERISK_OUTBOUND_CONTEXT", "crm-outbound"),
    "ORIGINATE_TIMEOUT": 30,
    # Asterisk dialplan CRMga hodisa yuborganda ishlatadigan maxfiy token
    "WEBHOOK_TOKEN": os.environ.get("ASTERISK_WEBHOOK_TOKEN", ""),
}

# Ovoz yozuvlari shu papkaga yuklanadi. Ular ochiq URL orqali emas, faqat ruxsat tekshiriladigan view orqali beriladi.
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Testlarda fon rejimida git fetch qilinmasin
UPDATE_CHECK_DISABLED = "test" in sys.argv
