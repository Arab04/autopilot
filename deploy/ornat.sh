#!/usr/bin/env bash
# Operator paneli va Telegram botni serverga o'rnatish yoki yangilash (Ubuntu/Debian).
#
# Serverda root sifatida bitta buyruq:
#   curl -fsSL https://raw.githubusercontent.com/Arab04/autopilot/claude/project-thread-gxkale/deploy/ornat.sh | bash
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
  git -C "$DIR" fetch -q origin "$BRANCH"
  git -C "$DIR" checkout -q -B "$BRANCH" "origin/$BRANCH"
else
  git clone -q --branch "$BRANCH" "$REPO" "$DIR"
fi
chown -R skuter: "$DIR"

IP="$(curl -fsS -4 --max-time 5 https://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')"
if [ ! -f "$ENVF" ]; then
  PAROL="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
  cat > "$ENVF" <<EOF
OPERATOR_PAROL=$PAROL
TELEGRAM_TOKEN=${TELEGRAM_TOKEN:-}
OPERATOR_CHATLAR=${OPERATOR_CHATLAR:-}
PANEL_URL=http://$IP:$PORT
EOF
else
  # Berilgan qiymatlar bilan yangilash (berilmaganlari o'zgarmaydi)
  for k in TELEGRAM_TOKEN OPERATOR_CHATLAR; do
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

systemctl daemon-reload
systemctl enable -q skuter-operator
systemctl restart skuter-operator

if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow "$PORT/tcp" >/dev/null
fi

sleep 3
systemctl --no-pager --lines=5 status skuter-operator || true
echo
echo "Operator paneli: http://$IP:$PORT"
echo "Login: operator   Parol: $(grep '^OPERATOR_PAROL=' "$ENVF" | cut -d= -f2-)"
grep -q '^TELEGRAM_TOKEN=.\+' "$ENVF" && echo "Telegram bot yoqilgan. Operatorlar: $(grep '^OPERATOR_CHATLAR=' "$ENVF" | cut -d= -f2-)" \
  || echo "Telegram bot o'chiq: TELEGRAM_TOKEN=... bilan qayta ishga tushiring"
