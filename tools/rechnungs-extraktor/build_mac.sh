#!/bin/bash
# Baut "Rechnungs-Extraktor.app" nach dist/
cd "$(dirname "$0")"
.venv/bin/pyinstaller --noconfirm --windowed --name "Rechnungs-Extraktor" \
  --hidden-import keyring.backends.macOS --collect-submodules webview launcher.py
