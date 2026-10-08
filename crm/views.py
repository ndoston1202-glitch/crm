import csv
import io
from functools import wraps
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from notifications.services import notify
from telephony.stats import call_stats, fmt_seconds
from telephony.utils import normalize_phone

from .forms import CallForm, LeadForm, LeadImportForm, SaleForm, ServiceOrderForm
from .models import Call, Lead, Sale, ServiceOrder

User = get_user_model()


def module_required(module):
    """Sahifani faqat shu modulga ruxsati bor foydalanuvchilar ochadi."""

    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.can(module):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def visible_leads(user):
    qs = Lead.objects.select_related("operator")
    if not user.can("leads"):
        return qs.none()
    if user.is_manager:
        return qs
    return qs.filter(operator=user)


def visible_orders(user):
    qs = ServiceOrder.objects.select_related("sale__lead", "sale__service", "assignee")
    if not user.can("orders"):
        return qs.none()
    if user.is_manager:
        return qs
    return qs.filter(assignee=user)


@login_required
def dashboard(request):
    """Bosh sahifa: foydalanuvchiga ruxsat berilgan birinchi bo'lim."""
    from accounts.permissions import HOME_ORDER

    for module, url_name in HOME_ORDER:
        if request.user.can(module):
            return redirect(url_name)
    return render(request, "crm/no_access.html")


@module_required("dashboard")
def dashboard_page(request):
    from .analytics import dashboard_data

    data = dashboard_data(request.user)
    hr_pending = None
    if request.user.can("hr"):
        from hr.models import LeaveRequest

        hr_pending = LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count()
    return render(request, "crm/dashboard.html", {"d": data, "hr_pending": hr_pending, "chart": {
        "series": data["series"], "funnel": data["funnel"], "sources": data["sources"],
    }})


@module_required("leads")
def my_work(request):
    user = request.user
    now = timezone.now()
    end_of_day = timezone.localtime(now).replace(hour=23, minute=59, second=59)
    leads = visible_leads(user).exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])
    context = {
        "new_leads": leads.filter(status=Lead.Status.NEW)[:50],
        "overdue": leads.filter(next_call_at__lt=now).order_by("next_call_at")[:50],
        "today": leads.filter(next_call_at__gte=now, next_call_at__lte=end_of_day).order_by("next_call_at"),
        "calls_today": Call.objects.filter(operator=user, created_at__date=timezone.localdate()).count(),
        "sales_today": Sale.objects.filter(operator=user, created_at__date=timezone.localdate()).count(),
    }
    return render(request, "crm/my_work.html", context)


@module_required("leads")
def lead_list(request):
    leads = visible_leads(request.user)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    source = request.GET.get("source", "")
    operator = request.GET.get("operator", "")
    if q:
        leads = leads.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(extra_phone__icontains=q))
    if status:
        leads = leads.filter(status=status)
    if source:
        leads = leads.filter(source=source)
    if operator and request.user.is_manager:
        leads = leads.filter(operator_id=operator) if operator != "none" else leads.filter(operator__isnull=True)
    page = Paginator(leads, 30).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "crm/lead_list.html",
        {
            "page": page,
            "statuses": Lead.Status.choices,
            "sources": Lead.Source.choices,
            "operators": User.objects.filter(role=User.Role.OPERATOR, is_active=True),
            "filters": {"q": q, "status": status, "source": source, "operator": operator},
            "querystring": params.urlencode(),
        },
    )


@module_required("leads")
def lead_kanban(request):
    leads = visible_leads(request.user)
    if request.user.is_manager and request.GET.get("operator"):
        leads = leads.filter(operator_id=request.GET["operator"])
    columns = []
    for value, label in Lead.Status.choices:
        column_leads = leads.filter(status=value)
        columns.append({"status": value, "label": label, "count": column_leads.count(), "leads": column_leads[:100]})
    return render(
        request,
        "crm/lead_kanban.html",
        {"columns": columns, "operators": User.objects.filter(role=User.Role.OPERATOR, is_active=True)},
    )


@module_required("leads")
def lead_create(request):
    form = LeadForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        lead = form.save(commit=False)
        lead.created_by = request.user
        lead._actor_id = request.user.pk
        if request.user.is_operator:
            lead.operator = request.user
        lead.save()
        messages.success(request, _("Lid qo'shildi"))
        return redirect("crm:lead_detail", pk=lead.pk)
    duplicates = []
    phone = request.POST.get("phone", "").strip()
    if phone:
        duplicates = Lead.objects.filter(phone=phone)[:5]
    return render(request, "crm/lead_form.html", {"form": form, "duplicates": duplicates})


@module_required("leads")
def lead_edit(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    form = LeadForm(request.POST or None, instance=lead, user=request.user)
    if request.method == "POST" and form.is_valid():
        lead._actor_id = request.user.pk
        form.save()
        messages.success(request, _("Saqlandi"))
        return redirect("crm:lead_detail", pk=lead.pk)
    return render(request, "crm/lead_form.html", {"form": form, "lead": lead})


@module_required("leads")
def lead_detail(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    return render(
        request,
        "crm/lead_detail.html",
        {
            "lead": lead,
            "calls": lead.calls.filter(phone_call__isnull=True).select_related("operator"),
            "phone_calls": lead.phone_calls.select_related("operator").prefetch_related("notes"),
            "sales": lead.sales.select_related("service", "operator", "order__assignee"),
            "call_form": CallForm(initial={"new_status": lead.status}),
            "sale_form": SaleForm(),
        },
    )


@module_required("leads")
@require_POST
def lead_set_status(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    status = request.POST.get("status")
    if status not in Lead.Status.values:
        return JsonResponse({"ok": False, "error": "bad status"}, status=400)
    if status == Lead.Status.WON and not lead.sales.exists():
        return JsonResponse({"ok": False, "error": _("Avval lid kartasida sotuvni rasmiylashtiring")}, status=400)
    lead.status = status
    lead.save(update_fields=["status", "updated_at"])
    return JsonResponse({"ok": True})


@module_required("leads")
@require_POST
def call_add(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    form = CallForm(request.POST)
    if form.is_valid():
        call = form.save(commit=False)
        call.lead = lead
        call.operator = request.user
        # Izohni shu operatorning ushbu lid bilan oxirgi ATS qo'ng'irog'iga bog'laymiz
        call.phone_call = (
            lead.phone_calls.filter(operator=request.user, notes__isnull=True, started_at__gte=timezone.now() - timedelta(hours=2))
            .order_by("-started_at")
            .first()
        )
        call.save()
        new_status = form.cleaned_data["new_status"]
        if new_status == Lead.Status.WON and not lead.sales.exists():
            messages.warning(request, _("Sotuv holatiga o'tkazish uchun quyida sotuvni rasmiylashtiring"))
            new_status = Lead.Status.INTERESTED
        lead.status = new_status
        lead.next_call_at = form.cleaned_data["next_call_at"]
        lead._actor_id = request.user.pk
        if lead.operator_id is None and request.user.is_operator:
            lead.operator = request.user
        lead.save()
        messages.success(request, _("Qo'ng'iroq natijasi saqlandi"))
    else:
        messages.error(request, _("Formada xatolik bor"))
    return redirect("crm:lead_detail", pk=lead.pk)


@module_required("leads")
@require_POST
def sale_add(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    form = SaleForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            sale = form.save(commit=False)
            sale.lead = lead
            sale.operator = lead.operator or request.user
            sale.save()
            order = ServiceOrder(
                sale=sale,
                assignee=form.cleaned_data["assignee"],
                scheduled_at=form.cleaned_data["scheduled_at"],
                address=form.cleaned_data["address"] or lead.region,
            )
            order._actor_id = request.user.pk
            order.save()
            lead.status = Lead.Status.WON
            lead.next_call_at = None
            lead.save()
        messages.success(request, _("Sotuv rasmiylashtirildi va xizmat buyurtmasi yaratildi"))
    else:
        messages.error(request, _("Sotuv formasida xatolik bor"))
    return redirect("crm:lead_detail", pk=lead.pk)


@module_required("import")
def lead_import(request):
    form = LeadImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        raw = form.cleaned_data["file"].read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1251")
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t") if text.strip() else csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        created, skipped = 0, 0
        operator = form.cleaned_data["operator"]
        leads = []
        for row in reader:
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            if not row.get("phone"):
                skipped += 1
                continue
            source = row.get("source", "")
            leads.append(
                Lead(
                    full_name=row.get("full_name") or row["phone"],
                    phone=row["phone"],
                    phone_norm=normalize_phone(row["phone"]),
                    region=row.get("region", ""),
                    comment=row.get("comment", ""),
                    source=source if source in Lead.Source.values else Lead.Source.OTHER,
                    operator=operator,
                    created_by=request.user,
                )
            )
        Lead.objects.bulk_create(leads)
        created = len(leads)
        if operator and created and operator != request.user:
            notify(
                operator, "lead", _("Sizga %(n)s ta yangi lid biriktirildi") % {"n": created},
                url=reverse("crm:my_work"),
            )
        messages.success(request, _("Import qilindi: %(c)s ta, o'tkazib yuborildi: %(s)s ta") % {"c": created, "s": skipped})
        return redirect("crm:lead_list")
    return render(request, "crm/lead_import.html", {"form": form})


@module_required("orders")
def order_list(request):
    orders = visible_orders(request.user)
    status = request.GET.get("status", "")
    if status:
        orders = orders.filter(status=status)
    page = Paginator(orders, 30).get_page(request.GET.get("page"))
    return render(
        request, "crm/order_list.html", {"page": page, "statuses": ServiceOrder.Status.choices, "status": status}
    )


@module_required("orders")
def order_edit(request, pk):
    order = get_object_or_404(visible_orders(request.user), pk=pk)
    form = ServiceOrderForm(request.POST or None, instance=order, user=request.user)
    if request.method == "POST" and form.is_valid():
        order = form.save(commit=False)
        order._actor_id = request.user.pk
        if order.status == ServiceOrder.Status.DONE and order.completed_at is None:
            order.completed_at = timezone.now()
        elif order.status != ServiceOrder.Status.DONE:
            order.completed_at = None
        order.save()
        messages.success(request, _("Buyurtma yangilandi"))
        return redirect("crm:order_list")
    return render(request, "crm/order_form.html", {"form": form, "order": order})


@module_required("reports")
def reports(request):
    today = timezone.localdate()
    date_from = parse_date(request.GET.get("from", "") or "") or today - timedelta(days=29)
    date_to = parse_date(request.GET.get("to", "") or "") or today

    leads = Lead.objects.filter(created_at__date__range=(date_from, date_to))
    calls = Call.objects.filter(created_at__date__range=(date_from, date_to))
    sales = Sale.objects.filter(created_at__date__range=(date_from, date_to))

    total_leads = leads.count()
    total_sales = sales.count()
    revenue = sales.aggregate(s=Sum("amount"))["s"] or 0

    by_status = {row["status"]: row["n"] for row in leads.values("status").annotate(n=Count("id"))}
    funnel = [
        {"label": label, "count": by_status.get(value, 0), "pct": round(100 * by_status.get(value, 0) / total_leads) if total_leads else 0}
        for value, label in Lead.Status.choices
    ]

    lead_counts = dict(leads.values_list("operator").annotate(n=Count("id")))
    call_counts = dict(calls.values_list("operator").annotate(n=Count("id")))
    sale_rows = {r["operator"]: r for r in sales.values("operator").annotate(n=Count("id"), s=Sum("amount"))}
    phone_totals, phone_by_op = call_stats(date_from, date_to)
    phone_totals["talk"] = fmt_seconds(phone_totals["talk"])
    phone_totals["avg"] = fmt_seconds(phone_totals["avg"])
    operators = []
    for op in User.objects.filter(role=User.Role.OPERATOR, is_active=True):
        n_leads = lead_counts.get(op.pk, 0)
        sale = sale_rows.get(op.pk, {})
        n_sales = sale.get("n", 0)
        operators.append(
            {
                "user": op,
                "leads": n_leads,
                "calls": call_counts.get(op.pk, 0),
                "sales": n_sales,
                "revenue": sale.get("s") or 0,
                "conversion": round(100 * n_sales / n_leads, 1) if n_leads else 0,
                "phone": {
                    "total": phone_by_op.get(op.pk, {}).get("total", 0),
                    "answered": phone_by_op.get(op.pk, {}).get("answered", 0),
                    "missed": phone_by_op.get(op.pk, {}).get("missed", 0),
                    "talk": fmt_seconds(phone_by_op.get(op.pk, {}).get("talk")),
                    "avg": fmt_seconds(phone_by_op.get(op.pk, {}).get("avg")),
                },
            }
        )
    operators.sort(key=lambda r: r["revenue"], reverse=True)

    by_source = [
        {"label": Lead.Source(r["source"]).label, "n": r["n"]}
        for r in leads.values("source").annotate(n=Count("id")).order_by("-n")
    ]
    orders = ServiceOrder.objects.filter(created_at__date__range=(date_from, date_to))
    order_status = {r["status"]: r["n"] for r in orders.values("status").annotate(n=Count("id"))}

    from .analytics import daily_series

    trend = daily_series(date_from, min(date_to, date_from + timedelta(days=365)), Lead.objects.all(), Sale.objects.all())
    return render(
        request,
        "crm/reports.html",
        {
            "trend": trend,
            "date_from": date_from,
            "date_to": date_to,
            "total_leads": total_leads,
            "total_calls": calls.count(),
            "total_sales": total_sales,
            "revenue": revenue,
            "conversion": round(100 * total_sales / total_leads, 1) if total_leads else 0,
            "funnel": funnel,
            "phone": phone_totals,
            "operators": operators,
            "by_source": by_source,
            "orders": [{"label": label, "n": order_status.get(v, 0)} for v, label in ServiceOrder.Status.choices],
            "unassigned": Lead.objects.filter(operator__isnull=True).exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).count(),
        },
    )
