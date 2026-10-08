# CRM — call-markaz uchun lidlar va sotuv tizimi

Lidlar kiritiladi → operatorlar qo'ng'iroq qiladi → sotuv rasmiylashtiriladi → xizmat ko'rsatiladi.
O'zbek va rus tillarida. Asterisk IP-telefoniyasi bilan ishlaydi.

## Windows'da o'rnatish (3 qadam)

1. Papkani kompyuterga yuklab oling (GitHub → **Code → Download ZIP** va arxivni oching, yoki `git clone`).
2. **`Ornatish.bat`** ni ikki marta bosing. U o'zi Python, Git va FFmpeg ni o'rnatadi, bazani tayyorlaydi,
   administrator parolini so'raydi va ish stolida **CRM** belgisini (logo bilan) yaratadi.
3. Ish stolidagi **CRM** belgisini bosing — dastur ishga tushadi va brauzerda ochiladi.

Operatorlar o'z kompyuterlaridan brauzerda `http://<server-kompyuter-IP>:8000` manzilini ochadi.

## Yangilash

Yangi versiya chiqqanda o'ng yuqoridagi 🔔 qo'ng'iroqchada xabar paydo bo'ladi.
**Yangilash** menyusi → **Yangilashni o'rnatish** — dastur o'zi yangilanadi va qayta ishga tushadi.

## Imkoniyatlar

| Modul | Nima qiladi |
|---|---|
| **Lidlar** | Qo'lda kiritish, CSV import, qidiruv/filtr, dublikat raqam haqida ogohlantirish |
| **Voronka** | Kanban: Yangi → Ishlanmoqda → Qayta qo'ng'iroq → Qiziqdi → Sotuv / Rad etildi |
| **Operator ish joyi** | Bugungi va muddati o'tgan qo'ng'iroqlar, qo'ng'iroq natijasi va izohi |
| **Sotuv va xizmat** | Sotuvdan so'ng xizmat buyurtmasi, servis xodimiga biriktirish |
| **IP-telefoniya** | Bir bosishda qo'ng'iroq, kiruvchi qo'ng'iroq oynasi, MP3 ovoz yozuvlari lid kartasida |
| **Telefon ilovasi (Android)** | Operator telefonida yozilgan qo'ng'iroqlarni CRMga avtomatik yuklaydi (`mobile/android`). iPhone uchun — lid kartasidan qo'lda yuklash |
| **Bildirishnomalar 🔔** | Qo'ng'iroq vaqti keldi, yangi lid biriktirildi, yangi buyurtma, o'tkazib yuborilgan qo'ng'iroq, yangi versiya |
| **Hisobotlar** | Lidlar, sotuvlar, konversiya, tushum, operatorlar reytingi, qo'ng'iroq statistikasi |

Rollar: **Administrator/Menejer** (hammasi), **Operator** (faqat o'z lidlari), **Xizmat xodimi** (faqat o'z buyurtmalari).
Foydalanuvchilar va xizmatlar **Sozlamalar** bo'limida qo'shiladi.

## Papkalar

| Papka | Ichida |
|---|---|
| `Ornatish.bat`, `Ishga_tushirish.bat` | O'rnatish va ishga tushirish |
| `crm/` | Lidlar, voronka, sotuv, hisobotlar |
| `telephony/` | Asterisk integratsiyasi |
| `notifications/` | Bildirishnomalar |
| `system/` | Dastur ichidan yangilash |
| `accounts/` | Foydalanuvchilar va rollar |
| `templates/`, `static/` | Interfeys |
| `mobile/android/` | Android ilova (APK GitHub Actions'da yig'iladi → Releases → `android-latest`) |
| `docs/` | Asterisk ulash yo'riqnomasi |
| `tools/` | O'rnatuvchi va tarjima skriptlari |

## Asterisk

Ulash yo'riqnomasi: [docs/asterisk.md](docs/asterisk.md). Sozlamalar `.env` faylida (o'rnatuvchi yaratadi).

## Dasturchilar uchun (Linux/macOS)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # va ffmpeg: apt install ffmpeg
python manage.py migrate
python manage.py seed_demo               # demo: admin / operator1 / servis1, parol demo12345
python manage.py runserver
python manage.py test
```

PostgreSQL uchun `.env` ga `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` yozing.
Yangi matn qo'shgach rus tarjimasi: `python tools/compile_translations.py`.
