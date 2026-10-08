import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from crm.models import Lead, Service

User = get_user_model()

NAMES = ["Aliyev Vali", "Karimova Nodira", "Toshmatov Bobur", "Rahimova Dilnoza", "Yusupov Jasur",
         "Saidova Malika", "Ergashev Sardor", "Qodirova Zarina", "Nazarov Akmal", "Usmonova Gulnora"]
REGIONS = ["Toshkent", "Samarqand", "Buxoro", "Farg'ona", "Andijon", "Namangan"]


class Command(BaseCommand):
    help = "Demo foydalanuvchilar, xizmatlar va lidlarni yaratadi (parol: demo12345)"

    def handle(self, *args, **options):
        users = [
            ("admin", "Admin", User.Role.ADMIN),
            ("operator1", "Operator 1", User.Role.OPERATOR),
            ("operator2", "Operator 2", User.Role.OPERATOR),
            ("servis1", "Servis xodimi", User.Role.SERVICE),
        ]
        created = {}
        for username, first_name, role in users:
            user, new = User.objects.get_or_create(username=username, defaults={"first_name": first_name, "role": role})
            if new:
                user.set_password("demo12345")
                user.is_staff = user.is_superuser = role == User.Role.ADMIN
                user.save()
            created[username] = user

        for name, price in [("Konditsioner o'rnatish", 450000), ("Internet ulash", 150000), ("Texnik xizmat", 200000)]:
            Service.objects.get_or_create(name=name, defaults={"price": price})

        if not Lead.objects.exists():
            operators = [created["operator1"], created["operator2"], None]
            for i, name in enumerate(NAMES * 3):
                Lead.objects.create(
                    full_name=name,
                    phone=f"+99890{random.randint(1000000, 9999999)}",
                    region=random.choice(REGIONS),
                    source=random.choice(Lead.Source.values),
                    status=random.choice([Lead.Status.NEW, Lead.Status.IN_PROGRESS, Lead.Status.CALLBACK, Lead.Status.INTERESTED]),
                    operator=operators[i % 3],
                )
        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar tayyor. Loginlar: admin, operator1, operator2, servis1 / demo12345"))
