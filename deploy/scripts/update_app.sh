#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/comparador-ipasgo}"

cd "$APP_DIR"
"$APP_DIR/.venv/bin/pip" install -r requirements-prod.txt
"$APP_DIR/.venv/bin/python" -m compileall app
"$APP_DIR/.venv/bin/python" -m pytest
sudo systemctl restart comparador-ipasgo
sudo systemctl status comparador-ipasgo --no-pager
