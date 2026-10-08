from django.contrib.auth import get_user_model

from .models import Notification

ICONS = {
    "callback": "bi-alarm",
    "lead": "bi-person-plus",
    "order": "bi-tools",
    "missed": "bi-telephone-x",
    "update": "bi-cloud-arrow-down",
    "leave": "bi-calendar2-check",
}


def notify(users, kind, title, text="", url="", key=""):
    """Bir yoki bir nechta foydalanuvchiga bildirishnoma. key berilsa, takroriy yozilmaydi."""
    if users is None:
        return
    if not hasattr(users, "__iter__"):
        users = [users]
    for user in users:
        if user is None:
            continue
        if key:
            Notification.objects.get_or_create(
                user=user, key=key, defaults={"kind": kind, "title": title[:200], "text": text[:500], "url": url}
            )
        else:
            Notification.objects.create(user=user, kind=kind, title=title[:200], text=text[:500], url=url)


def managers():
    """Barcha ma'lumotlarni ko'radigan rahbarlar (to'liq dostup yoki "hammasi" doirasi)."""
    from django.db.models import Q

    User = get_user_model()
    return User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(full_access=True) | Q(data_scope="all"))
