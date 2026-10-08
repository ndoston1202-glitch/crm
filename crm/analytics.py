"""Dashboard va analitika uchun hisob-kitoblar. Ma'lumot doirasi foydalanuvchi ruxsatiga bog'liq."""
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from telephony.models import PhoneCall

from .models import Call, Lead, Sale, ServiceOrder


def scoped(user):
    """(lidlar, sotuvlar, qo'ng'iroq natijalari, ATS qo'ng'iroqlari) — foydalanuvchi ko'rishi mumkin bo'lganlari."""
    leads, sales, calls, phone = Lead.objects.all(), Sale.objects.all(), Call.objects.all(), PhoneCall.objects.all()
    if not user.is_manager:
        leads, sales = leads.filter(operator=user), sales.filter(operator=user)
        calls, phone = calls.filter(operator=user), phone.filter(operator=user)
    return leads, sales, calls, phone


def daily_series(date_from, date_to, leads, sales):
    """Kunlar bo'yicha: lidlar soni, sotuvlar soni, tushum."""
    tz = timezone.get_current_timezone()

    def by_day(qs, **agg):
        return {
            row["d"]: row
            for row in qs.filter(created_at__date__range=(date_from, date_to))
            .annotate(d=TruncDate("created_at", tzinfo=tz))
            .values("d")
            .annotate(**agg)
        }

    lead_rows = by_day(leads, n=Count("id"))
    sale_rows = by_day(sales, n=Count("id"), s=Sum("amount"))
    days, lead_n, sale_n, revenue = [], [], [], []
    day = date_from
    while day <= date_to:
        days.append(day.strftime("%d.%m"))
        lead_n.append(lead_rows.get(day, {}).get("n", 0))
        sale_n.append(sale_rows.get(day, {}).get("n", 0))
        revenue.append(float(sale_rows.get(day, {}).get("s") or 0))
        day += timedelta(days=1)
    return {"labels": days, "leads": lead_n, "sales": sale_n, "revenue": revenue}


def _period(leads, sales, calls, phone, start, end):
    n_leads = leads.filter(created_at__date__range=(start, end)).count()
    s = sales.filter(created_at__date__range=(start, end)).aggregate(n=Count("id"), s=Sum("amount"))
    n_calls = calls.filter(created_at__date__range=(start, end)).count() + phone.filter(
        started_at__date__range=(start, end)
    ).exclude(status=PhoneCall.Status.RINGING).count()
    return {
        "leads": n_leads,
        "sales": s["n"],
        "revenue": float(s["s"] or 0),
        "calls": n_calls,
        "conversion": round(100 * s["n"] / n_leads, 1) if n_leads else 0,
    }


def dashboard_data(user):
    today = timezone.localdate()
    leads, sales, calls, phone = scoped(user)
    month_start = today.replace(day=1)
    now = timezone.now()
    open_leads = leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST])

    status_counts = dict(open_leads.values_list("status").annotate(n=Count("id")))
    funnel = [{"label": str(label), "n": status_counts.get(value, 0)} for value, label in Lead.Status.choices
              if value not in (Lead.Status.WON, Lead.Status.LOST)]
    month_leads = leads.filter(created_at__date__gte=month_start)
    sources = [
        {"label": str(Lead.Source(r["source"]).label), "n": r["n"]}
        for r in month_leads.values("source").annotate(n=Count("id")).order_by("-n")
    ]
    orders = ServiceOrder.objects.all()
    if not user.is_manager:
        orders = orders.filter(assignee=user) if user.can("orders") else orders.none()

    data = {
        "today": _period(leads, sales, calls, phone, today, today),
        "yesterday": _period(leads, sales, calls, phone, today - timedelta(days=1), today - timedelta(days=1)),
        "month": _period(leads, sales, calls, phone, month_start, today),
        "series": daily_series(today - timedelta(days=29), today, leads, sales),
        "funnel": funnel,
        "sources": sources,
        "overdue": open_leads.filter(next_call_at__lt=now).count(),
        "unassigned": Lead.objects.filter(operator__isnull=True).exclude(
            status__in=[Lead.Status.WON, Lead.Status.LOST]).count() if user.is_manager else None,
        "orders_open": orders.filter(status__in=[ServiceOrder.Status.NEW, ServiceOrder.Status.IN_PROGRESS]).count(),
        "missed_today": phone.filter(
            direction=PhoneCall.Direction.INCOMING, started_at__date=today
        ).exclude(status__in=[PhoneCall.Status.ANSWERED, PhoneCall.Status.RINGING]).count(),
    }
    if user.is_manager:
        top = (
            Sale.objects.filter(created_at__date__gte=month_start, operator__isnull=False)
            .values("operator__first_name", "operator__last_name", "operator__username")
            .annotate(n=Count("id"), s=Sum("amount"))
            .order_by("-s")[:5]
        )
        data["top"] = [
            {"name": f"{r['operator__first_name']} {r['operator__last_name']}".strip() or r["operator__username"],
             "n": r["n"], "s": float(r["s"] or 0)}
            for r in top
        ]
    return data
