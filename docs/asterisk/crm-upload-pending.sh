#!/bin/sh
# Zaxira: biror sabab bilan (CRM o'chiq, tarmoq uzilgan) yuklanmay qolgan yozuvlarni qayta yuboradi.
# crontab -e:  */10 * * * * /usr/local/bin/crm-upload-pending.sh
MONITOR=/var/spool/asterisk/monitor

# 5 daqiqadan eski fayllar (hozir yozilayotganlariga tegmaymiz)
find "$MONITOR" -maxdepth 1 -type f \( -name '*.wav' -o -name '*.mp3' \) -mmin +5 | while read -r FILE; do
    NAME=$(basename "$FILE"); NAME=${NAME%.*}
    case "$NAME" in
        crm-*) KEY="call_id=${NAME#crm-}" ;;   # CRMdan qilingan chiquvchi qo'ng'iroq
        *)     KEY="uniqueid=$NAME" ;;         # kiruvchi qo'ng'iroq
    esac
    /usr/local/bin/crm-upload.sh "$KEY" "$FILE"
done
