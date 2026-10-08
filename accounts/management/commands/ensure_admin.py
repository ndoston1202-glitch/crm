import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Administrator foydalanuvchisini yaratadi yoki parolini yangilaydi (o'rnatuvchi uchun)"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", help="yoki CRM_ADMIN_PASSWORD muhit o'zgaruvchisi")

    def handle(self, *args, username, password, **options):
        password = password or os.environ.get("CRM_ADMIN_PASSWORD", "")
        if len(password) < 6:
            raise CommandError("Parol kamida 6 belgidan iborat bo'lishi kerak")
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"first_name": "Administrator"})
        user.role = User.Role.ADMIN
        user.is_staff = user.is_superuser = True
        user.full_access = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Administrator {'yaratildi' if created else 'yangilandi'}: {username}"))
