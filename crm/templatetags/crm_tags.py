from django import template

register = template.Library()

STATUS_COLORS = {
    "new": "primary",
    "in_progress": "info",
    "callback": "warning",
    "interested": "secondary",
    "won": "success",
    "lost": "danger",
    "done": "success",
    "cancelled": "danger",
}


@register.filter
def status_color(value):
    return STATUS_COLORS.get(value, "secondary")


@register.simple_tag(takes_context=True)
def nav_active(context, *names):
    match = context["request"].resolver_match
    return "active" if match and match.url_name in names else ""
