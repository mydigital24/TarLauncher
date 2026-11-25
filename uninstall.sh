#!/usr/bin/env bash
set -e

INSTALL_DIR="${HOME}/.local/share/gearleverfortar-app"
APPS_DIR="${HOME}/.local/share/applications"
ICON_FILE="${HOME}/.local/share/icons/hicolor/256x256/apps/gearleverfortar.png"

echo "Entferne Gear Lever for Tar ..."
rm -rf "${INSTALL_DIR}"
rm -f "${APPS_DIR}/gearleverfortar.desktop"
rm -f "${ICON_FILE}"
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPS_DIR}" || true
fi
echo "Fertig."