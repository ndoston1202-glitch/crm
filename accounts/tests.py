import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

User = get_user_model()


class EnsureAdminTests(TestCase):
    def test_password_from_env(self):
        with mock.patch.dict(os.environ, {"CRM_ADMIN_PASSWORD": "secret123"}):
            call_command("ensure_admin", stdout=open(os.devnull, "w"))
        admin = User.objects.get(username="admin")
        self.assertTrue(admin.check_password("secret123"))
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)

    def test_empty_password_rejected(self):
        with mock.patch.dict(os.environ, {"CRM_ADMIN_PASSWORD": ""}):
            with self.assertRaises(CommandError):
                call_command("ensure_admin", password="")
        self.assertFalse(User.objects.exists())

    def test_reset_existing_password(self):
        User.objects.create_user("admin", password="old")
        call_command("ensure_admin", password="newpass1", stdout=open(os.devnull, "w"))
        self.assertTrue(User.objects.get(username="admin").check_password("newpass1"))
