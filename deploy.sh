#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
VENV_DIR="$REPO_ROOT/.venv"
BIND="${BIND:-127.0.0.1:8001}"

if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "缺少 $REPO_ROOT/.env，请先复制 .env.example 并填写生产配置。"
    exit 1
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$REPO_ROOT[production]"

cd "$BACKEND_DIR"
"$VENV_DIR/bin/python" manage.py check

DB_PATH="$BACKEND_DIR/data/backend.sqlite3"
if [ -f "$DB_PATH" ]; then
    BACKUP_DIR="$REPO_ROOT/backups"
    BACKUP_PATH="$BACKUP_DIR/backend-pre-deploy-$(date +%Y%m%d-%H%M%S).sqlite3"
    mkdir -p "$BACKUP_DIR"
    "$VENV_DIR/bin/python" - "$DB_PATH" "$BACKUP_PATH" <<'PY'
import sqlite3
import sys

source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
with target:
    source.backup(target)
target.close()
source.close()
print(f"数据库部署前备份完成：{sys.argv[2]}")
PY
fi

"$VENV_DIR/bin/python" manage.py migrate --noinput
"$VENV_DIR/bin/python" manage.py collectstatic --noinput

if [ "${1:-}" = "--install-service" ]; then
    if [ "$(id -u)" -ne 0 ]; then
        echo "安装 systemd 服务需要 root 权限：sudo bash deploy.sh --install-service"
        exit 1
    fi
    cat > /etc/systemd/system/xinhuo-django.service <<EOF
[Unit]
Description=Xinhuo Django
After=network.target

[Service]
Type=notify
User=${SUDO_USER:-root}
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$REPO_ROOT/.env
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/gunicorn config.wsgi:application --bind $BIND --workers 2 --threads 2 --access-logfile - --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now xinhuo-django
    echo "xinhuo-django 已安装并启动。"
    exit 0
fi

exec "$VENV_DIR/bin/gunicorn" config.wsgi:application --bind "$BIND" --workers 2 --threads 2 --access-logfile - --error-logfile -
