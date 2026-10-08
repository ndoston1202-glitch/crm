from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from crm.models import Lead

from .models import Notification
from .services import ICONS, notify


def _due_callbacks(user):
    """Operatorning qo'ng'iroq vaqti kelgan lidlari uchun bildirishnoma yaratadi (har bir vaqt uchun bir marta)."""
    if not user.can("leads"):
        return
    leads = Lead.objects.filter(operator=user, next_call_at__lte=timezone.now()).exclude(
        status__in=[Lead.Status.WON, Lead.Status.LOST]
    )
    for lead in leads[:50]:
        local = timezone.localtime(lead.next_call_at)
        notify(
            user,
            "callback",
            _("Qo'ng'iroq vaqti keldi: %(name)s") % {"name": lead.full_name},
            text=f"{lead.phone} · {local:%d.%m %H:%M}",
            url=reverse("crm:lead_detail", args=[lead.pk]),
            key=f"callback:{lead.pk}:{lead.next_call_at.timestamp():.0f}",
        )


@login_required
def poll(request):
    user = request.user
    _due_callbacks(user)
    if user.can("update"):
        from system.updates import maybe_notify_update

        maybe_notify_update()
    qs = Notification.objects.filter(user=user)
    items = [
        {
            "id": n.pk,
            "kind": n.kind,
            "icon": ICONS.get(n.kind, "bi-bell"),
            "title": n.title,
            "text": n.text,
            "is_read": n.is_read,
            "time": timezone.localtime(n.created_at).strftime("%d.%m %H:%M"),
            "url": reverse("notifications:go", args=[n.pk]),
        }
        for n in qs[:15]
    ]
    return JsonResponse({"unread": qs.filter(is_read=False).count(), "items": items})


@login_required
def go(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    return redirect(n.url or "crm:dashboard")


@login_required
@require_POST
def read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})
