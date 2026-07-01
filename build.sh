#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "ExileFilterStudio" \
  --paths "src" \
  app.py

echo "Binário criado em dist/ExileFilterStudio/ExileFilterStudio"
