from django.db.models import Avg, Count, Q, Sum

from .models import PhoneCall


def call_stats(date_from, date_to):
    calls = PhoneCall.objects.filter(started_at__date__range=(date_from, date_to)).exclude(status=PhoneCall.Status.RINGING)
    answered = Q(status=PhoneCall.Status.ANSWERED)
    missed_in = Q(direction=PhoneCall.Direction.INCOMING) & ~answered
    agg = dict(
        total=Count("id"),
        incoming=Count("id", filter=Q(direction=PhoneCall.Direction.INCOMING)),
        outgoing=Count("id", filter=Q(direction=PhoneCall.Direction.OUTGOING)),
        answered=Count("id", filter=answered),
        missed=Count("id", filter=missed_in),
        talk=Sum("duration", filter=answered),
        avg=Avg("duration", filter=answered),
    )
    totals = calls.aggregate(**agg)
    per_operator = {row["operator"]: row for row in calls.values("operator").annotate(**agg)}
    return totals, per_operator


def fmt_seconds(value):
    value = int(value or 0)
    h, rem = divmod(value, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
