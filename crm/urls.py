from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard_page, name="dashboard_page"),
    path("my/", views.my_work, name="my_work"),
    path("leads/", views.lead_list, name="lead_list"),
    path("leads/kanban/", views.lead_kanban, name="lead_kanban"),
    path("leads/new/", views.lead_create, name="lead_create"),
    path("leads/import/", views.lead_import, name="lead_import"),
    path("leads/<int:pk>/", views.lead_detail, name="lead_detail"),
    path("leads/<int:pk>/edit/", views.lead_edit, name="lead_edit"),
    path("leads/<int:pk>/status/", views.lead_set_status, name="lead_set_status"),
    path("leads/<int:pk>/call/", views.call_add, name="call_add"),
    path("leads/<int:pk>/sale/", views.sale_add, name="sale_add"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_edit, name="order_edit"),
    path("reports/", views.reports, name="reports"),
]
