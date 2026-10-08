from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Lead, Sale, Service, ServiceOrder

User = get_user_model()


class CrmFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)
        self.op1 = User.objects.create_user("op1", password="x", role=User.Role.OPERATOR)
        self.op2 = User.objects.create_user("op2", password="x", role=User.Role.OPERATOR)
        self.srv = User.objects.create_user("srv", password="x", role=User.Role.SERVICE)
        self.service = Service.objects.create(name="Montaj", price=100)
        self.lead = Lead.objects.create(full_name="Vali", phone="+998901112233", operator=self.op1)

    def test_operator_sees_only_own_leads(self):
        Lead.objects.create(full_name="Begona Lid", phone="1", operator=self.op2)
        self.client.force_login(self.op1)
        resp = self.client.get(reverse("crm:lead_list"))
        self.assertContains(resp, "Vali")
        self.assertNotContains(resp, "Begona Lid")
        other = Lead.objects.get(full_name="Begona Lid")
        self.assertEqual(self.client.get(reverse("crm:lead_detail", args=[other.pk])).status_code, 404)

    def test_call_updates_lead(self):
        self.client.force_login(self.op1)
        self.client.post(
            reverse("crm:call_add", args=[self.lead.pk]),
            {"result": "callback", "note": "ertaga", "new_status": "callback", "next_call_at": "2030-01-01T10:00"},
        )
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CALLBACK)
        self.assertIsNotNone(self.lead.next_call_at)
        self.assertEqual(self.lead.calls.count(), 1)

    def test_won_requires_sale(self):
        self.client.force_login(self.op1)
        resp = self.client.post(reverse("crm:lead_set_status", args=[self.lead.pk]), {"status": "won"})
        self.assertEqual(resp.status_code, 400)

    def test_sale_creates_service_order(self):
        self.client.force_login(self.op1)
        self.client.post(
            reverse("crm:sale_add", args=[self.lead.pk]),
            {"service": self.service.pk, "amount": "150000", "assignee": self.srv.pk, "address": "Chilonzor"},
        )
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.WON)
        order = ServiceOrder.objects.get()
        self.assertEqual(order.assignee, self.srv)
        self.assertEqual(Sale.objects.get().operator, self.op1)

        self.client.force_login(self.srv)
        self.client.post(reverse("crm:order_edit", args=[order.pk]), {"status": "done", "address": "Chilonzor"})
        order.refresh_from_db()
        self.assertEqual(order.status, ServiceOrder.Status.DONE)
        self.assertIsNotNone(order.completed_at)

    def test_import_and_reports(self):
        self.client.force_login(self.admin)
        csv_file = SimpleUploadedFile("l.csv", "full_name;phone;source\nAli;+99890;instagram\nBo'sh;;\n".encode())
        self.client.post(reverse("crm:lead_import"), {"file": csv_file, "operator": self.op2.pk})
        self.assertTrue(Lead.objects.filter(full_name="Ali", operator=self.op2, source="instagram").exists())
        self.assertEqual(self.client.get(reverse("crm:reports")).status_code, 200)
        self.assertEqual(self.client.get(reverse("crm:lead_kanban")).status_code, 200)

    def test_operator_cannot_open_reports(self):
        self.client.force_login(self.op1)
        self.assertEqual(self.client.get(reverse("crm:reports")).status_code, 403)
        self.assertEqual(self.client.get(reverse("crm:my_work")).status_code, 200)

    def test_russian_ui(self):
        self.client.force_login(self.admin)
        self.client.cookies["django_language"] = "ru"
        self.assertContains(self.client.get(reverse("crm:reports")), "Отчёты")
