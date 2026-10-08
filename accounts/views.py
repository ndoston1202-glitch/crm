from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from crm.views import module_required

from .forms import UserAccessForm
from .models import User
from .permissions import MODULES, ROLE_DEFAULTS


@module_required("users")
def user_list(request):
    users = User.objects.order_by("-is_active", "role", "username")
    labels = dict(MODULES)
    rows = [
        {"user": u, "modules": [labels[m] for m in (u.modules or []) if m in labels]}
        for u in users
    ]
    return render(request, "accounts/user_list.html", {"rows": rows})


@module_required("users")
def user_edit(request, pk=None):
    instance = get_object_or_404(User, pk=pk) if pk else User()
    form = UserAccessForm(request.POST or None, instance=instance, editor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Saqlandi"))
        return redirect("accounts:user_list")
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "obj": instance if pk else None, "role_defaults": ROLE_DEFAULTS},
    )
