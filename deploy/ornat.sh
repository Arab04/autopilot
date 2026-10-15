#!/usr/bin/env bash
# Operator paneli va Telegram botni serverga o'rnatish yoki yangilash (Ubuntu/Debian).
#
# Serverda root sifatida bitta buyruq:
#   curl -fsSL https://raw.githubusercontent.com/Arab04/autopilot/claude/project-thread-gxkale/deploy/ornat.sh | bash
# Login/parolni o'zgartirish:
#   curl -fsSL .../deploy/ornat.sh | OPERATOR_LOGIN=admin OPERATOR_PAROL=yangi_parol bash
# HTTPS (telefon kamerasi faqat HTTPS da ishlaydi) avtomatik: <ip>.sslip.io domeni va Let's Encrypt
# sertifikati; serverda nginx bo'lsa unga alohida sayt qo'shiladi, bo'lmasa Caddy o'rnatiladi. O'z domeningiz bo'lsa: DOMEN=panel.misol.uz; o'chirish: HTTPS=0.
# Telegram bot bilan (token @BotFather dan):
#   curl -fsSL .../deploy/ornat.sh | TELEGRAM_TOKEN=123:ABC OPERATOR_CHATLAR=111,222 bash
#
# Qayta ishga tushirilsa: kodni yangilaydi va xizmatni qayta yoqadi; parol va sozlamalar saqlanadi.
# Sozlamalar: /etc/skuter-operator.env (o'zgartirgandan keyin: systemctl restart skuter-operator)
set -euo pipefail

BRANCH="${BRANCH:-claude/project-thread-gxkale}"
REPO="${REPO:-https://github.com/Arab04/autopilot.git}"
DIR=/opt/autopilot
ENVF=/etc/skuter-operator.env
PORT="${PORT:-8765}"

[ "$(id -u)" = 0 ] || { echo "root sifatida ishga tushiring (sudo bash)"; exit 1; }

if ! command -v git >/dev/null || ! command -v python3 >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git python3 ca-certificates
fi

id skuter >/dev/null 2>&1 || useradd --system --home "$DIR" --shell /usr/sbin/nologin skuter

if [ -d "$DIR/.git" ]; then
  git config --global --get-all safe.directory | grep -qx "$DIR" || git config --global --add safe.directory "$DIR"
  git -C "$DIR" fetch -q origin "$BRANCH"
  git -C "$DIR" checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  git clone -q --branch "$BRANCH" "$REPO" "$DIR"
fi
chown -R skuter: "$DIR"

IP="$(curl -fsS -4 --max-time 5 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
if [ ! -f "$ENVF" ]; then
  PAROL="${OPERATOR_PAROL:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')}"
  cat > "$ENVF" <<EOF
OPERATOR_LOGIN=${OPERATOR_LOGIN:-operator}
OPERATOR_PAROL=$PAROL
TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-}
OPERATOR_CHATLAR=${OPERATOR_CHATLAR:-}
PANEL_URL=http://$IP:$PORT
EOF
else
  # Berilgan qiymatlar bilan yangilash (berilmaganlari o'zgarmaydi)
  for k in OPERATOR_LOGIN OPERATOR_PAROL TELEGRAM_TOKEN OPERATOR_CHATLAR; do
    v="${!k:-}"
    if [ -n "$v" ]; then
      grep -q "^$k=" "$ENVF" && sed -i "s|^$k=.*|$k=$v|" "$ENVF" || echo "$k=$v" >> "$ENVF"
    fi
  done
fi
chmod 600 "$ENVF"

cat > /etc/systemd/system/skuter-operator.service <<EOF
[Unit]
Description=Skuter operator paneli va Telegram bot (simulyator)
After=network-online.target
Wants=network-online.target

[Service]
User=skuter
WorkingDirectory=$DIR/sim/world
EnvironmentFile=$ENVF
ExecStart=/usr/bin/python3 -u operator_panel.py --host 0.0.0.0 --port $PORT --davomli
Restart=always
RestartSec=5
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

HTTPS="${HTTPS:-1}"
DOMEN="${DOMEN:-${IP//./-}.sslip.io}"
# Serverda boshqa saytlar bo'lishi mumkin: ularning sozlamalariga tegilmaydi, panel alohida sayt sifatida qo'shiladi.
if [ "$HTTPS" = 1 ] && systemctl is-active -q nginx; then
  # nginx allaqachon 80/443 da: alohida server bloki + certbot (faqat shu domen uchun)
  if [ -d /etc/nginx/sites-enabled ]; then NGF=/etc/nginx/sites-available/skuter-operator; else NGF=/etc/nginx/conf.d/skuter-operator.conf; fi
  if [ ! -f "$NGF" ]; then
    cat > "$NGF" <<NGINX
# skuter-operator (deploy/ornat.sh)
server {
    listen 80;
    listen [::]:80;
    server_name $DOMEN;
    client_max_body_size 3m;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_buffering off;          # kamera oqimi (MJPEG) darhol o'tsin
        proxy_read_timeout 1h;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
NGINX
    [ -d /etc/nginx/sites-enabled ] && ln -sf "$NGF" /etc/nginx/sites-enabled/skuter-operator
  fi
  if nginx -t 2>/dev/null; then
    systemctl reload nginx
    if ! command -v certbot >/dev/null; then
      DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx || true
    fi
    certbot --nginx -d "$DOMEN" --non-interactive --agree-tos --register-unsafely-without-email --redirect \
      --keep-until-expiring -q || { echo "DIQQAT: sertifikat olinmadi (certbot), panel faqat http orqali"; HTTPS=0; }
  else
    echo "DIQQAT: nginx sozlamasi xato bo'ldi, panel bloki olib tashlandi (boshqa saytlarga tegilmadi)"
    rm -f /etc/nginx/sites-enabled/skuter-operator "$NGF"
    HTTPS=0
  fi
  # Avvalgi versiya o'rnatgan, lekin port band bo'lgani uchun ishlamayotgan Caddy ni o'chirish
  if command -v caddy >/dev/null && ! systemctl is-active -q caddy; then systemctl disable -q caddy 2>/dev/null || true; fi
elif [ "$HTTPS" = 1 ] && ss -tln | grep -qE ':(80|443) ' && ! systemctl is-active -q caddy; then
  echo "DIQQAT: 80/443 portni boshqa dastur egallagan (nginx emas), HTTPS o'rnatilmadi: ss -tlnp | grep -E ':(80|443) '"
  HTTPS=0
elif [ "$HTTPS" = 1 ]; then
  if ! command -v caddy >/dev/null; then
    { apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy; } \
      || { echo "DIQQAT: Caddy o'rnatilmadi, panel faqat http orqali ochiladi"; HTTPS=0; }
  fi
  if [ "$HTTPS" = 1 ]; then
    # Panel alohida faylda; Caddyfile ga faqat import qatori qo'shiladi (boshqa saytlar o'zgarmaydi).
    # flush_interval -1: kamera oqimi (MJPEG) buferlanmasdan darhol o'tsin
    cat > /etc/caddy/skuter-operator.caddy <<CADDY
$DOMEN {
	reverse_proxy 127.0.0.1:$PORT {
		flush_interval -1
	}
}
CADDY
    CF=/etc/caddy/Caddyfile
    if ! grep -q 'import /etc/caddy/skuter-operator.caddy' "$CF" 2>/dev/null; then
      [ -f "$CF" ] && cp "$CF" "$CF.bak.$(date +%s)"
      if [ -f "$CF" ] && grep -q '/usr/share/caddy' "$CF" && [ "$(grep -c '{' "$CF")" -le 3 ]; then
        : > "$CF"  # paket bilan kelgan namuna fayl (":80 { root * /usr/share/caddy ... }")
      fi
      echo 'import /etc/caddy/skuter-operator.caddy' >> "$CF"
    fi
    if caddy validate --config "$CF" --adapter caddyfile >/dev/null 2>&1; then
      systemctl enable -q caddy
      systemctl reload-or-restart caddy || echo "DIQQAT: Caddy ishga tushmadi: journalctl -u caddy"
    else
      echo "DIQQAT: Caddyfile xato, o'zgartirilmadi: caddy validate --config $CF"
      HTTPS=0
    fi
  fi
fi
if [ "$HTTPS" = 1 ]; then
  sed -i "s|^PANEL_URL=.*|PANEL_URL=https://$DOMEN|" "$ENVF"
fi

systemctl daemon-reload
systemctl enable -q skuter-operator
systemctl restart skuter-operator

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow "$PORT/tcp" >/dev/null
  if [ "$HTTPS" = 1 ]; then ufw allow 80,443/tcp >/dev/null; fi
fi

sleep 3
systemctl --no-pager --lines=5 status skuter-operator || true
echo
if [ "$HTTPS" = 1 ]; then
  echo "Operator paneli: https://$DOMEN   (yoki http://$IP:$PORT)"
  echo "Telefon kamerasi: https://$DOMEN/kamera"
else
  echo "Operator paneli: http://$IP:$PORT"
fi
LOGIN="$(grep '^OPERATOR_LOGIN=' "$ENVF" | cut -d= -f2-)"
echo "Login: ${LOGIN:-operator}   Parol: $(grep '^OPERATOR_PAROL=' "$ENVF" | cut -d= -f2-)"
grep -q '^TELEGRAM_TOKEN=.\+' "$ENVF" && echo "Telegram bot yoqilgan. Operatorlar: $(grep '^OPERATOR_CHATLAR=' "$ENVF" | cut -d= -f2-)" \
  || echo "Telegram bot o'chiq: TELEGRAM_TOKEN=... bilan qayta ishga tushiring"
