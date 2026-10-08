from django.contrib import admin

from .models import Call, Lead, Sale, Service, ServiceOrder


class CallInline(admin.TabularInline):
    model = Call
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "source", "status", "operator", "created_at")
    list_filter = ("status", "source", "operator")
    search_fields = ("full_name", "phone")
    inlines = [CallInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("lead", "service", "amount", "operator", "created_at")
    list_filter = ("service", "operator")


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ("sale", "assignee", "status", "scheduled_at")
    list_filter = ("status", "assignee")
