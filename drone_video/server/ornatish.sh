#!/usr/bin/env bash
# Serverni tayyorlaydi: parollarni yaratadi, mediamtx.local.yml yozadi va pult hamda
# operator uchun manzillarni parollar.txt ga chiqaradi.
#
#   ./ornatish.sh SERVER_MANZILI            (masalan: ./ornatish.sh 203.0.113.10)
#   ./ornatish.sh SERVER_MANZILI --qayta    yangi parollar bilan qayta yozish
set -euo pipefail
cd "$(dirname "$0")"

SERVER="${1:?Server manzilini (tashqi IP yoki domen) bering: ./ornatish.sh 203.0.113.10}"
if [[ ! "$SERVER" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "Noto'g'ri manzil: $SERVER" >&2
  exit 1
fi

if [[ -f mediamtx.local.yml && "${2:-}" != "--qayta" ]]; then
  echo "mediamtx.local.yml allaqachon bor, parollar o'zgartirilmadi (yangisi kerak bo'lsa: --qayta)."
  echo
  cat parollar.txt
  exit 0
fi

parol() { od -An -N12 -tx1 /dev/urandom | tr -d ' \n'; }
PULT_PAROLI=$(parol)
OPERATOR_PAROLI=$(parol)

sed -e "s|PULT_PAROLI|$PULT_PAROLI|" \
    -e "s|OPERATOR_PAROLI|$OPERATOR_PAROLI|" \
    -e "s|SERVER_MANZILI|$SERVER|" \
    mediamtx.yml > mediamtx.local.yml
mkdir -p recordings

cat > parollar.txt <<EOF
Telefon yoki pultdagi Larix Screencaster (SRT, tavsiya etiladi):
  URL:       srt://$SERVER:8890
  Mode:      Caller
  streamid:  publish:dron:pult:$PULT_PAROLI
  Bitta qatorda: srt://$SERVER:8890?streamid=publish:dron:pult:$PULT_PAROLI

Larix Screencaster (RTMP, SRT ishlamasa):
  rtmp://$SERVER:1935/dron?user=pult&pass=$PULT_PAROLI

Operator, brauzerda (login: operator, parol: $OPERATOR_PAROLI):
  http://$SERVER:8889/dron     WebRTC, kechikish ~0,5 s
  http://$SERVER:8888/dron     HLS, kechikish 3-6 s

Operator, VLC yoki Python:
  rtsp://operator:$OPERATOR_PAROLI@$SERVER:8554/dron

Serverning o'zidagi dasturlar uchun (parolsiz):
  rtsp://127.0.0.1:8554/dron

Sinov (kompyuterdan, telefon o'rnida):
  ./oqim.sh sinov $SERVER $PULT_PAROLI
  ./oqim.sh tekshir $SERVER $OPERATOR_PAROLI
EOF
chmod 600 parollar.txt mediamtx.local.yml

cat parollar.txt
echo
echo "Keyingi qadamlar:"
echo "  docker compose up -d"
echo "  sudo ufw allow 8890/udp && sudo ufw allow 1935/tcp && sudo ufw allow 8554/tcp \\"
echo "    && sudo ufw allow 8888/tcp && sudo ufw allow 8889/tcp && sudo ufw allow 8189/udp"
