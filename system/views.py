from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from crm.views import manager_required

from . import updates


@manager_required
def update(request):
    context = {"version": updates.current_version(), "git": updates.git_available(), "can_restart": updates.can_restart()}
    if request.GET.get("check"):
        try:
            context["commits"] = updates.check_updates()
        except Exception as exc:
            context["error"] = str(exc)
    return render(request, "system/update.html", context)


@manager_required
@require_POST
def apply(request):
    try:
        log = updates.apply_update()
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("system:update")
    restarting = updates.schedule_restart()
    return render(request, "system/update_done.html", {"log": log, "restarting": restarting})


def ping(request):
    return JsonResponse({"ok": True, "version": updates.current_version()["hash"]})
