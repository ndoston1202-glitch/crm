from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CrmUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "phone", "sip_extension", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("CRM", {"fields": ("role", "phone", "sip_extension")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CRM", {"fields": ("first_name", "last_name", "role", "phone", "sip_extension")}),)
