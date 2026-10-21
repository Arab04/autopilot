#!/usr/bin/env bash
# Avtomatik joylash (CD): serverda har 2 daqiqada systemd taymeri ishga tushiradi (deploy/cd-yoqish.sh o'rnatadi).
#
# 1. GitHub dagi branchda yangi commit bormi? Yo'q bo'lsa - hech narsa qilmaydi.
# 2. Shu commit uchun CI (GitHub Actions sinovlari) tugaganmi va hammasi yashilmi?
#    Hali ishlayotgan bo'lsa - keyingi safar yana tekshiradi. Qizil bo'lsa - joylamaydi (bir marta xabar beradi).
# 3. Yashil bo'lsa: shu commitdagi deploy/ornat.sh ni ishga tushiradi (kod yangilanadi, xizmat qayta yoqiladi,
#    parol va sozlamalar saqlanadi).
# 4. Panel javob bermasa - avvalgi commitga qaytaradi.
# Natija: journalctl -u skuter-cd ; Telegram bot yoqilgan bo'lsa operatorlarga ham xabar ketadi.
#
# Branch: /etc/skuter-operator.env dagi DEPLOY_BRANCH, bo'lmasa serverda hozir turgan branch.
set -euo pipefail

DIR="${DIR:-/opt/autopilot}"
ENVF="${ENVF:-/etc/skuter-operator.env}"
HOLAT="${HOLAT:-/var/lib/skuter-cd}"
API="${API:-https://api.github.com/repos/Arab04/autopilot}"
SOGLIK_URL="${SOGLIK_URL:-http://127.0.0.1:8765/}"
ORNAT="${ORNAT:-bash}"            # sinov uchun almashtiriladi
QAYTA_YOQ="${QAYTA_YOQ:-systemctl restart skuter-operator}"

mkdir -p "$HOLAT"
exec 9>"$HOLAT/lock"
flock -n 9 || exit 0              # oldingi joylash hali tugamagan

qiymat() { [ -f "$ENVF" ] && grep "^$1=" "$ENVF" | tail -1 | cut -d= -f2- || true; }

xabar() {
  echo "$1"
  local token chatlar
  token="$(qiymat TELEGRAM_TOKEN)"; chatlar="$(qiymat OPERATOR_CHATLAR)"
  [ -n "$token" ] && [ -n "$chatlar" ] || return 0
  for c in ${chatlar//,/ }; do
    curl -fsS --max-time 10 "https://api.telegram.org/bot$token/sendMessage" \
      --data-urlencode "chat_id=$c" --data-urlencode "text=Server: $1" >/dev/null 2>&1 || true
  done
}

git config --global --get-all safe.directory 2>/dev/null | grep -qx "$DIR" || git config --global --add safe.directory "$DIR"
BRANCH="$(qiymat DEPLOY_BRANCH)"
[ -n "$BRANCH" ] || BRANCH="$(git -C "$DIR" rev-parse --abbrev-ref HEAD)"
ESKI="$(git -C "$DIR" rev-parse HEAD)"
YANGI="$(git -C "$DIR" ls-remote origin "refs/heads/$BRANCH" | cut -f1)"
[ -n "$YANGI" ] || { echo "GitHub da $BRANCH branchi topilmadi"; exit 1; }
[ "$YANGI" != "$ESKI" ] || exit 0
[ "$(cat "$HOLAT/rad" 2>/dev/null || true)" != "$YANGI" ] || exit 0   # bu commit CI dan o'tmagan, kutamiz

# CI natijasi (ochiq repo: tokensiz GitHub API)
CI="$(curl -fsS --max-time 20 -H "Accept: application/vnd.github+json" "$API/commits/$YANGI/check-runs?per_page=100" \
  | python3 -c '
import json, sys
runs = json.load(sys.stdin).get("check_runs", [])
if not runs or any(r["status"] != "completed" for r in runs):
    print("kutish")
else:
    yomon = sorted({r["name"] for r in runs if r["conclusion"] not in ("success", "skipped", "neutral")})
    print("qizil " + ",".join(yomon) if yomon else "yashil")
')" || { echo "GitHub API ga ulanib bo'lmadi, keyinroq"; exit 0; }

QISQA="${YANGI:0:7}"
case "$CI" in
  kutish) echo "$QISQA: CI hali tugamagan, keyingi tekshiruvda"; exit 0 ;;
  qizil*) echo "$YANGI" > "$HOLAT/rad"
          xabar "$BRANCH $QISQA joylanmadi: CI sinovlari o'tmadi (${CI#qizil }). Server eski versiyada ishlayapti."
          exit 0 ;;
esac

git -C "$DIR" fetch -q origin "$BRANCH"
SARLAVHA="$(git -C "$DIR" log -1 --format=%s "$YANGI")"
echo "$QISQA joylanmoqda: $SARLAVHA"
SKRIPT="$(mktemp)"
git -C "$DIR" show "$YANGI:deploy/ornat.sh" > "$SKRIPT"
if BRANCH="$BRANCH" $ORNAT "$SKRIPT" > "$HOLAT/oxirgi.log" 2>&1; then OK=1; else OK=0; fi
rm -f "$SKRIPT"

# Sog'liq tekshiruvi: panel 401 (parol so'raydi) yoki 200 qaytarishi kerak
SOG=0
for _ in $(seq 1 10); do
  kod="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$SOGLIK_URL" || true)"
  if [ "$kod" = 401 ] || [ "$kod" = 200 ]; then SOG=1; break; fi
  sleep 3
done

if [ "$OK" = 1 ] && [ "$SOG" = 1 ]; then
  xabar "yangi versiya joylandi: $QISQA $SARLAVHA"
  # Joylash skriptining o'zi ham yangilanib borsin
  if [ -f "$DIR/deploy/avto-yangilash.sh" ] && [ -n "${OZI:-}" ]; then install -m 755 "$DIR/deploy/avto-yangilash.sh" "$OZI"; fi
else
  git -C "$DIR" checkout -q -B "$BRANCH" "$ESKI"
  $QAYTA_YOQ || true
  echo "$YANGI" > "$HOLAT/rad"
  xabar "$QISQA joylanganda panel ishlamadi, avvalgi versiyaga (${ESKI:0:7}) qaytarildi. Log: $HOLAT/oxirgi.log"
  exit 1
fi
