#!/bin/sh
# MixMonitor yozuvni yopgandan keyin ishga tushadi va faylni CRMga yuklaydi.
# Foydalanish: crm-upload.sh uniqueid=1700000000.12 /var/spool/asterisk/monitor/1700000000.12.wav
# O'rnatish: cp crm-upload.sh /usr/local/bin/ && chmod +x /usr/local/bin/crm-upload.sh
#            /etc/asterisk/crm.env faylida CRM_URL va CRM_TOKEN ni yozing.
. /etc/asterisk/crm.env

KEY_VALUE="$1"
FILE="$2"
[ -s "$FILE" ] || exit 0

# Joy tejash uchun mp3 ga o'tkazish (lame o'rnatilgan bo'lsa)
if command -v lame >/dev/null 2>&1; then
    lame --quiet -V 6 "$FILE" "${FILE%.wav}.mp3" && rm -f "$FILE" && FILE="${FILE%.wav}.mp3"
fi

for i in 1 2 3 4 5; do
    if curl -sf -m 120 -F "token=$CRM_TOKEN" -F "$KEY_VALUE" -F "file=@$FILE" "$CRM_URL/telephony/upload/" >/dev/null; then
        rm -f "$FILE"   # CRMga yuklandi — ATS serverida saqlash shart emas
        exit 0
    fi
    sleep $((i * 10))
done
logger -t crm-upload "Yuklab bo'lmadi: $FILE"
exit 1
