#!/usr/bin/env bash

# Direktori proyek di home user VPS
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Jalankan menggunakan python di virtualenv terisolasi
"$APP_DIR/venv/bin/python3" "$APP_DIR/bot.py" --once
