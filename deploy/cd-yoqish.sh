#!/usr/bin/env bash
# Avtomatik joylashni (CD) yoqish: serverda root sifatida bir marta.
#   curl -fsSL https://raw.githubusercontent.com/Arab04/autopilot/claude/project-thread-gxkale/deploy/cd-yoqish.sh | bash
# Shundan keyin GitHub ga push qilingan har bir commit CI sinovlaridan o'tsa, 2 daqiqa ichida serverga o'zi joylanadi.
# Kuzatish: journalctl -u skuter-cd -f      O'chirish: systemctl disable --now skuter-cd.timer
# Boshqa branchdan joylash (masalan PR lar birlashtirilgach): /etc/skuter-operator.env ga DEPLOY_BRANCH=main
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "root sifatida ishga tushiring"; exit 1; }
[ -d /opt/autopilot/.git ] || { echo "Avval panelni o'rnating: deploy/ornat.sh"; exit 1; }

SRC="https://raw.githubusercontent.com/Arab04/autopilot/${BRANCH:-claude/project-thread-gxkale}/deploy/avto-yangilash.sh"
curl -fsSL "$SRC" -o /usr/local/sbin/skuter-avto-yangilash
chmod 755 /usr/local/sbin/skuter-avto-yangilash

cat > /etc/systemd/system/skuter-cd.service <<'EOF'
[Unit]
Description=Skuter paneli: GitHub dagi yangi commitni CI yashil bo'lsa joylash
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
Environment=OZI=/usr/local/sbin/skuter-avto-yangilash
ExecStart=/usr/local/sbin/skuter-avto-yangilash
TimeoutStartSec=15min
EOF

cat > /etc/systemd/system/skuter-cd.timer <<'EOF'
[Unit]
Description=Skuter paneli: har 2 daqiqada yangi versiyani tekshirish

[Timer]
OnBootSec=2min
OnUnitActiveSec=2min
RandomizedDelaySec=15s

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now skuter-cd.timer
systemctl start skuter-cd.service || true
echo
B="$(grep '^DEPLOY_BRANCH=' /etc/skuter-operator.env 2>/dev/null | cut -d= -f2- || true)"
echo "Avtomatik joylash yoqildi. Branch: ${B:-$(git -C /opt/autopilot rev-parse --abbrev-ref HEAD)}"
journalctl -u skuter-cd -n 5 --no-pager || true
