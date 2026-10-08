"""Dastur ichidan yangilash: git orqali yangi versiyani olib, kutubxonalar va bazani yangilaydi."""
import os
import shutil
import subprocess
import sys
import threading
import time

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.translation import gettext as _

ROOT = str(settings.BASE_DIR)
CHECK_INTERVAL = 60 * 60  # yangilanishni soatiga bir marta tekshiramiz
_lock = threading.Lock()


class UpdateError(Exception):
    pass


def _run(args, timeout=300):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    out = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise UpdateError(f"{' '.join(args[:3])}: {out}")
    return out


def git_available():
    return os.path.isdir(os.path.join(ROOT, ".git")) and shutil.which("git") is not None


def current_version():
    if not git_available():
        return {"hash": "—", "date": "", "branch": ""}
    try:
        info = _run(["git", "log", "-1", "--format=%h|%cd", "--date=format:%d.%m.%Y %H:%M"]).split("|")
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        return {"hash": info[0], "date": info[1], "branch": branch}
    except (UpdateError, subprocess.TimeoutExpired):
        return {"hash": "?", "date": "", "branch": ""}


def check_updates():
    """Serverdagi yangi o'zgarishlar ro'yxati: [{'hash','subject','date'}]."""
    if not git_available():
        raise UpdateError(_("Git topilmadi yoki dastur git orqali o'rnatilmagan"))
    _run(["git", "fetch", "--quiet"], timeout=120)
    try:
        _run(["git", "rev-parse", "--abbrev-ref", "@{u}"])
    except UpdateError:
        raise UpdateError(_("Joriy branch uchun server (upstream) sozlanmagan"))
    log = _run(["git", "log", "--format=%h|%s|%cd", "--date=format:%d.%m.%Y", "HEAD..@{u}"])
    commits = []
    for line in log.splitlines():
        h, _sep, rest = line.partition("|")
        subject, _sep, date = rest.rpartition("|")
        commits.append({"hash": h, "subject": subject, "date": date})
    cache.set("crm_update_available", len(commits), CHECK_INTERVAL)
    return commits


def apply_update():
    """Yangilanishni o'rnatadi va bajarilgan qadamlar jurnalini qaytaradi."""
    if not _lock.acquire(blocking=False):
        raise UpdateError(_("Yangilash allaqachon bajarilmoqda"))
    try:
        log = []
        steps = [
            (_("Yangi versiyani yuklab olish"), ["git", "pull", "--ff-only"]),
            (_("Kutubxonalarni yangilash"), [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"]),
            (_("Ma'lumotlar bazasini yangilash"), [sys.executable, "manage.py", "migrate", "--noinput"]),
            (_("Tarjimalarni yangilash"), [sys.executable, os.path.join("tools", "compile_translations.py")]),
        ]
        for title, args in steps:
            out = _run(args, timeout=600)
            log.append({"title": title, "output": out})
        cache.delete("crm_update_available")
        return log
    finally:
        _lock.release()


def can_restart():
    return os.environ.get("CRM_LAUNCHER") == "1"


def schedule_restart():
    """Ishga_tushirish.bat serverni 3-kod bilan to'xtaganini ko'rib, qayta ishga tushiradi."""
    if can_restart():
        threading.Timer(1.5, os._exit, args=(3,)).start()
        return True
    return False


def _background_check():
    from notifications.services import managers, notify

    try:
        commits = check_updates()
    except Exception:  # tarmoq yo'q va h.k. — keyingi safar urinamiz
        return
    if commits:
        notify(
            list(managers().distinct()),
            "update",
            _("Yangi versiya mavjud (%(n)s ta o'zgarish)") % {"n": len(commits)},
            text=commits[0]["subject"],
            url=reverse("system:update"),
            key=f"update:{commits[0]['hash']}",
        )


def maybe_notify_update():
    if not git_available() or getattr(settings, "UPDATE_CHECK_DISABLED", False):
        return
    if cache.add("crm_update_last_check", time.time(), CHECK_INTERVAL):
        threading.Thread(target=_background_check, daemon=True).start()
