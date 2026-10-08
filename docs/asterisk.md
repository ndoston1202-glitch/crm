# Asterisk IP-telefoniyani ulash

## Qanday ishlaydi

```
 Mijoz ──► Trunk ──► Asterisk ──(CURL webhook: ring/answer/hangup)──► CRM  ──► operator brauzerida oyna
                        │                                              ▲
                        └──(MixMonitor tugagach crm-upload.sh: fayl)───┘  ──► lid kartasida audio pleer
 Operator "Qo'ng'iroq" tugmasi ──► CRM ──(AMI Originate)──► Asterisk ──► avval operator, keyin mijoz
```

- **Kiruvchi qo'ng'iroq**: CRM raqam bo'yicha lidni topadi (oxirgi 9 raqam solishtiriladi). Topilmasa — yangi lid yaratadi
  (manba "Kiruvchi qo'ng'iroq"). Operator brauzerida mijoz kartasi bilan oyna chiqadi.
- **Bir bosishda qo'ng'iroq**: lid kartasidagi yashil tugma. Operator profilida *Ichki raqam (SIP)* to'ldirilgan bo'lishi shart.
- **Ovoz yozuvi** suhbat tugagach **avtomatik** CRMga yuklanadi (operator hech narsa qilmaydi), **MP3 (mono, 64 kbit/s, ~0,5 MB/daqiqa)** ga aylantiriladi,
  `MEDIA_ROOT/recordings/YYYY/MM/` ga saqlanadi va lid kartasida eshitiladi / MP3 sifatida yuklab olinadi.
  Yozuvni faqat menejer, shu qo'ng'iroq operatori yoki lidni ko'ra oladigan operator ochadi.
- Operator qo'ng'iroqdan keyin yozgan **natija va izoh** shu qo'ng'iroq yozuvi ostida ko'rinadi.
- **Hisobotlar**da: kiruvchi/chiquvchi, javob berilgan, o'tkazib yuborilgan, suhbat vaqti — operatorlar bo'yicha.

## 1. CRM sozlamalari (muhit o'zgaruvchilari)

| O'zgaruvchi | Misol | Izoh |
|---|---|---|
| `ASTERISK_AMI_HOST` | `10.0.0.10` | Asterisk server manzili |
| `ASTERISK_AMI_PORT` | `5038` | |
| `ASTERISK_AMI_USER` / `ASTERISK_AMI_SECRET` | `crm` / `...` | `manager.conf` dagi foydalanuvchi |
| `ASTERISK_CHANNEL_TEMPLATE` | `PJSIP/{extension}` | chan_sip bo'lsa `SIP/{extension}` |
| `ASTERISK_OUTBOUND_CONTEXT` | `crm-outbound` | |
| `ASTERISK_WEBHOOK_TOKEN` | uzun tasodifiy satr | Asterisk shu token bilan murojaat qiladi |
| `MEDIA_ROOT` | `/var/lib/crm/media` | yozuvlar saqlanadigan papka (zaxira nusxasini oling!) |

Token yaratish: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

Har bir operatorga **Sozlamalar → Users** bo'limida *Ichki raqam (SIP)* yozing (masalan `101`).

CRM serverida **ffmpeg** o'rnatilgan bo'lishi shart (`apt install ffmpeg`) — yozuvlar shu bilan MP3 ga o'tkaziladi.

Nginx orqasida bo'lsa `client_max_body_size 50m;` qo'ying (yozuv fayllari uchun).

## 2. Asterisk sozlamalari

Fayllar `docs/asterisk/` papkasida:

1. `manager_crm.conf` → `/etc/asterisk/manager.conf` ga qo'shing, `permit` ga CRM server IP sini yozing. `manager reload`.
2. `extensions_crm.conf` → `extensions.conf` ga qo'shing. `[globals]` da `CRM_URL`, `CRM_TOKEN` ni,
   `Dial(...)` da operatorlar ichki raqamlarini va `trunk` nomini o'zingiznikiga moslang. Trunkdan kelgan qo'ng'iroqlarni
   `crm-inbound` kontekstiga yo'naltiring. `dialplan reload`.
3. `crm-upload.sh` → `/usr/local/bin/`, `chmod +x`; `crm.env.example` → `/etc/asterisk/crm.env`.
   Zaxira uchun `crm-upload-pending.sh` ni ham `/usr/local/bin/` ga qo'ying va cron qo'shing:
   `*/10 * * * * /usr/local/bin/crm-upload-pending.sh` — CRM vaqtincha ishlamay qolsa ham yozuvlar yo'qolmaydi.
   Kerak: `curl`; ixtiyoriy: `lame` (faylni ATS serverida siqib yuboradi — trafik kamroq).

## 3. Tekshirish

```bash
# Asterisk serveridan CRM ga ulanishni tekshirish:
curl "https://crm.example.uz/telephony/webhook/?token=TOKEN&event=ring&direction=in&uniqueid=test1&phone=901234567"
# -> {"ok": true, ...} va CRMda shu raqam bilan lid paydo bo'ladi
```

Asterisk CLI da: `module show like curl`, `manager show users`.
