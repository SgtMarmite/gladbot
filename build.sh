#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Step 1: PyInstaller bundle ==="
.venv/bin/python -m PyInstaller gladbot.spec --noconfirm --clean
echo "PyInstaller output: dist/gladbot/"

echo ""
echo "=== Step 2: Install Electron dependencies ==="
cd electron
npm install

echo ""
echo "=== Step 3: Electron Builder ==="
npm run build

echo ""
echo "=== Done ==="
echo "Output: electron/dist/"
