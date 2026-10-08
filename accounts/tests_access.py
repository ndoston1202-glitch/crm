from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crm.models import Lead

User = get_user_model()


class AccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)
        self.op = User.objects.create_user("op", password="x", role=User.Role.OPERATOR)

    def test_role_defaults(self):
        self.assertTrue(self.admin.has_full_access)
        self.assertEqual(self.op.modules, ["dashboard", "leads", "phone_app"])
        self.assertFalse(self.op.is_manager)
        srv = User.objects.create_user("srv", password="x", role=User.Role.SERVICE)
        self.assertTrue(srv.can("orders"))
        self.assertFalse(srv.can("leads"))

    def test_limited_user_blocked_from_other_modules(self):
        self.client.force_login(self.op)
        self.assertEqual(self.client.get(reverse("crm:reports")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("hr:index")).status_code, 403)
        self.assertEqual(self.client.get(reverse("crm:dashboard_page")).status_code, 200)
        self.assertRedirects(self.client.get(reverse("crm:dashboard")), reverse("crm:dashboard_page"))

    def test_admin_grants_limited_access_with_all_data(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("accounts:user_edit", args=[self.op.pk]), {
            "first_name": "Ali", "last_name": "", "username": "op", "role": "operator", "phone": "", "sip_extension": "",
            "is_active": "on", "modules": ["leads", "reports"], "data_scope": "all", "password": "",
        })
        self.assertEqual(resp.status_code, 302, resp.content[:500])
        self.op.refresh_from_db()
        self.assertEqual(self.op.modules, ["leads", "reports"])
        self.assertTrue(self.op.is_manager)
        self.assertTrue(self.op.check_password("x"))  # parol o'zgarmadi
        Lead.objects.create(full_name="Begona", phone="1")
        self.client.force_login(self.op)
        self.assertContains(self.client.get(reverse("crm:lead_list")), "Begona")
        self.assertEqual(self.client.get(reverse("crm:reports")).status_code, 200)
        self.assertEqual(self.client.get(reverse("crm:dashboard_page")).status_code, 403)

    def test_create_user_with_full_access(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_create"), {
            "first_name": "Bosh", "username": "boss", "role": "manager", "is_active": "on",
            "full_access": "on", "data_scope": "all", "password": "Kuchli123!",
        })
        boss = User.objects.get(username="boss")
        self.assertTrue(boss.has_full_access)
        self.assertTrue(boss.is_staff)

    def test_limited_user_manager_cannot_escalate(self):
        hr = User.objects.create_user("hr", password="x", role=User.Role.MANAGER)
        hr.modules = ["users", "hr"]
        hr.save()
        self.client.force_login(hr)
        self.client.post(reverse("accounts:user_edit", args=[self.op.pk]), {
            "username": "op", "role": "operator", "is_active": "on", "full_access": "on",
            "modules": ["settings", "reports", "hr"], "data_scope": "own",
        })
        self.op.refresh_from_db()
        self.assertFalse(self.op.full_access)
        self.assertNotIn("settings", self.op.modules)
        self.assertNotIn("reports", self.op.modules)  # o'zida yo'q modulni bera olmaydi
        # to'liq dostupli adminni o'zgartira olmaydi
        resp = self.client.post(reverse("accounts:user_edit", args=[self.admin.pk]), {
            "username": "admin", "role": "admin", "is_active": "", "data_scope": "own"})
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_cannot_lock_self_out(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("accounts:user_edit", args=[self.admin.pk]), {
            "username": "admin", "role": "admin", "is_active": "on", "data_scope": "own"})
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.full_access)

    def test_settings_module_opens_admin_panel(self):
        self.op.modules = ["settings"]
        self.op.save()
        self.assertTrue(self.op.is_staff)
        self.client.force_login(self.op)
        self.assertEqual(self.client.get("/admin/crm/lead/").status_code, 200)
