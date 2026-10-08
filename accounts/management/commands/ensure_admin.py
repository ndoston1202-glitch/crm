from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Administrator foydalanuvchisini yaratadi yoki parolini yangilaydi (o'rnatuvchi uchun)"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", required=True)

    def handle(self, *args, username, password, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"first_name": "Administrator"})
        user.role = User.Role.ADMIN
        user.is_staff = user.is_superuser = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Administrator {'yaratildi' if created else 'yangilandi'}: {username}"))
