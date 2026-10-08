from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UpdateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", role=User.Role.ADMIN)
        self.op = User.objects.create_user("op", password="x", role=User.Role.OPERATOR)

    def test_operator_forbidden(self):
        self.client.force_login(self.op)
        self.assertEqual(self.client.get(reverse("system:update")).status_code, 403)

    @mock.patch("system.updates.git_available", return_value=True)
    @mock.patch("system.updates.check_updates", return_value=[{"hash": "abc123", "subject": "Yangi funksiya", "date": "08.10.2026"}])
    def test_check_shows_commits(self, *_):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("system:update") + "?check=1")
        self.assertContains(resp, "Yangi funksiya")
        self.assertContains(resp, reverse("system:apply"))

    @mock.patch("system.updates.schedule_restart", return_value=True)
    @mock.patch("system.updates.apply_update", return_value=[{"title": "git pull", "output": ""}])
    def test_apply_restarts(self, apply, restart):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("system:apply"))
        self.assertContains(resp, reverse("system:ping"))
        apply.assert_called_once()
        restart.assert_called_once()

    def test_ping(self):
        self.assertTrue(self.client.get(reverse("system:ping")).json()["ok"])
