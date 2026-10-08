from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from crm.models import Lead, Service

from .models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)
        self.op = User.objects.create_user("op", password="x", role=User.Role.OPERATOR)
        self.srv = User.objects.create_user("srv", password="x", role=User.Role.SERVICE)

    def poll(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("notifications:poll")).json()

    def test_lead_assigned_by_manager_notifies_operator(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("crm:lead_create"), {"full_name": "Vali", "phone": "901112233", "source": "other", "status": "new", "operator": self.op.pk})
        data = self.poll(self.op)
        self.assertEqual(data["unread"], 1)
        self.assertIn("Vali", data["items"][0]["title"])

    def test_operator_creating_own_lead_no_notification(self):
        self.client.force_login(self.op)
        self.client.post(reverse("crm:lead_create"), {"full_name": "Vali", "phone": "901112233", "source": "other", "status": "new"})
        self.assertFalse(Notification.objects.exists())

    def test_callback_due_once(self):
        Lead.objects.create(full_name="Vali", phone="1", operator=self.op, next_call_at=timezone.now() - timedelta(minutes=1))
        Lead.objects.create(full_name="Keyin", phone="2", operator=self.op, next_call_at=timezone.now() + timedelta(hours=1))
        self.poll(self.op)
        self.poll(self.op)
        callbacks = Notification.objects.filter(kind="callback")
        self.assertEqual(callbacks.count(), 1)  # faqat vaqti kelgani, va faqat bir marta
        self.assertIn("Vali", callbacks.get().title)

    def test_sale_notifies_service_worker_and_read(self):
        lead = Lead.objects.create(full_name="Vali", phone="1", operator=self.op)
        service = Service.objects.create(name="Montaj", price=1)
        self.client.force_login(self.op)
        self.client.post(reverse("crm:sale_add", args=[lead.pk]), {"service": service.pk, "amount": "5", "assignee": self.srv.pk})
        data = self.poll(self.srv)
        self.assertEqual(data["unread"], 1)
        resp = self.client.get(data["items"][0]["url"])
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.poll(self.srv)["unread"], 0)

    def test_read_all_and_isolation(self):
        Notification.objects.create(user=self.op, kind="lead", title="a")
        self.assertEqual(self.poll(self.admin)["unread"], 0)
        n = Notification.objects.get()
        self.assertEqual(self.client.get(reverse("notifications:go", args=[n.pk])).status_code, 404)
        self.client.force_login(self.op)
        self.client.post(reverse("notifications:read_all"))
        self.assertEqual(self.poll(self.op)["unread"], 0)

    @override_settings(ASTERISK={"WEBHOOK_TOKEN": "t"})
    def test_missed_call_notifies_operator(self):
        Lead.objects.create(full_name="Vali", phone="901112233", operator=self.op)
        Notification.objects.all().delete()
        hook = reverse("telephony:webhook")
        self.client.get(hook, {"token": "t", "event": "ring", "uniqueid": "m1", "phone": "901112233"})
        self.client.get(hook, {"token": "t", "event": "hangup", "uniqueid": "m1", "disposition": "NOANSWER"})
        self.assertEqual(Notification.objects.get().kind, "missed")
        self.assertEqual(Notification.objects.get().user, self.op)
