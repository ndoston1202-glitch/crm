from django.contrib import admin

from .models import PhoneCall


@admin.register(PhoneCall)
class PhoneCallAdmin(admin.ModelAdmin):
    list_display = ("started_at", "direction", "phone", "extension", "operator", "status", "duration", "lead")
    list_filter = ("direction", "status", "operator")
    search_fields = ("phone", "uniqueid")
    raw_id_fields = ("lead",)
