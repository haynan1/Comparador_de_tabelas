#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/comparador-ipasgo}"
DATA_DIR="${DATA_DIR:-/var/lib/comparador-ipasgo}"
SERVICE_FILE="/etc/systemd/system/comparador-ipasgo.service"
ENV_FILE="/etc/comparador-ipasgo.env"
NGINX_SITE="/etc/nginx/sites-available/comparador-ipasgo"

sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx

sudo mkdir -p "$APP_DIR" "$DATA_DIR/uploads" "$DATA_DIR/reports" "$DATA_DIR/processed"
sudo chown -R "$USER":"$USER" "$APP_DIR"
sudo chown -R www-data:www-data "$DATA_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-prod.txt"

if [ ! -f "$ENV_FILE" ]; then
  SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  sudo tee "$ENV_FILE" >/dev/null <<EOF
SECRET_KEY=$SECRET_KEY
APP_ENV=production
APP_DATA_DIR=$DATA_DIR
MAX_UPLOAD_MB=80
TRUST_PROXY=1
PREFERRED_URL_SCHEME=http
EOF
fi

sudo cp "$APP_DIR/deploy/systemd/comparador-ipasgo.service" "$SERVICE_FILE"
sudo cp "$APP_DIR/deploy/nginx/comparador-ipasgo.conf" "$NGINX_SITE"
sudo ln -sf "$NGINX_SITE" /etc/nginx/sites-enabled/comparador-ipasgo
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now comparador-ipasgo
sudo systemctl reload nginx

echo "Deploy concluido. Verifique com: systemctl status comparador-ipasgo"
