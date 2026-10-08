# CRM — call-markaz uchun lidlar va sotuv tizimi

Bitrix24 uslubidagi CRM: lidlar kiritiladi → operatorlar qo'ng'iroq qiladi → sotuv rasmiylashtiriladi → xizmat ko'rsatiladi.
Texnologiya: Django 5.1 + PostgreSQL (lokalda SQLite), Bootstrap 5. Interfeys: o'zbek va rus tillarida.

## Imkoniyatlar

| Modul | Nima qiladi |
|---|---|
| **Lidlar** | Qo'lda kiritish, CSV import, qidiruv/filtr, dublikat telefonni ogohlantirish |
| **Voronka (Kanban)** | Holatlar: Yangi → Ishlanmoqda → Qayta qo'ng'iroq → Qiziqdi → Sotuv / Rad etildi, drag-and-drop |
| **Operator ish joyi** | "Mening ishlarim": muddati o'tgan va bugungi qo'ng'iroqlar, yangi lidlar; qo'ng'iroq natijasi, izoh, keyingi qo'ng'iroq vaqti |
| **Sotuv va xizmat** | Sotuv rasmiylashtirilganda avtomatik xizmat buyurtmasi yaratiladi, servis xodimiga biriktiriladi, holati kuzatiladi |
| **IP-telefoniya (Asterisk)** | Bir bosishda qo'ng'iroq, kiruvchi qo'ng'iroqda mijoz kartasi oynasi, ovoz yozuvlari MP3 formatida CRMga yuklanadi va lid kartasida eshitiladi, operator izohi yozuv ostida |
| **Hisobotlar** | Davr bo'yicha: lidlar, qo'ng'iroqlar, sotuvlar, konversiya, tushum; operatorlar reytingi; manbalar |

## Rollar

- **Administrator / Menejer** — hamma narsani ko'radi, lidlarni operatorlarga biriktiradi, import, hisobotlar, sozlamalar (`/admin/`).
- **Operator** — faqat o'ziga biriktirilgan lidlar bilan ishlaydi.
- **Xizmat xodimi** — faqat o'ziga biriktirilgan xizmat buyurtmalarini ko'radi va holatini o'zgartiradi.

Foydalanuvchilar va xizmatlar (narxlar) `Sozlamalar` (Django admin) orqali qo'shiladi.

## Ishga tushirish

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # + ffmpeg: apt install ffmpeg
python manage.py migrate
python manage.py seed_demo        # demo ma'lumotlar (ixtiyoriy)
python manage.py runserver
```

http://127.0.0.1:8000 — loginlar: `admin`, `operator1`, `operator2`, `servis1`, parol `demo12345`.

### PostgreSQL

Muhit o'zgaruvchilarini bering: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
Productionda yana: `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS=crm.example.uz`.

### Asterisk

Ulash bo'yicha to'liq yo'riqnoma: [docs/asterisk.md](docs/asterisk.md). Tayyor dialplan, AMI va yuklash skripti `docs/asterisk/` da.

## Tarjimalar

Asosiy matnlar o'zbekcha yozilgan, rus tarjimasi `scripts/compile_translations.py` ichida.
Yangi matn qo'shgach: `python scripts/compile_translations.py`.

## Testlar

```bash
python manage.py test
```

## Keyingi bosqichlar (rejada)

- Ovoz yozuvlarini avtomatik matnga aylantirish (speech-to-text)
- Telegram bot / sayt formasidan lidlarni avtomatik qabul qilish (API)
- Lidlarni operatorlarga avtomatik taqsimlash
- SMS xabarnomalar, vazifalar va eslatmalar
