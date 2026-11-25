#!/usr/bin/env bash
set -e

APP_NAME="TarLauncher"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/gearleverfortar-app"
APPS_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

echo "Installiere ${APP_NAME} nach ${INSTALL_DIR} ..."
mkdir -p "${INSTALL_DIR}"
cp -r "${SRC_DIR}/." "${INSTALL_DIR}/"
chmod +x "${INSTALL_DIR}/main.py"

mkdir -p "${APPS_DIR}" "${ICON_DIR}"
# Icon (falls vorhanden, sonst generisch)
ICON_LINE="Icon=application-x-executable"
if [ -f "${SRC_DIR}/tarlauncher.svg" ]; then
  mkdir -p "${HOME}/.local/share/icons/hicolor/scalable/apps"
  cp "${SRC_DIR}/tarlauncher.svg" "${HOME}/.local/share/icons/hicolor/scalable/apps/tarlauncher.svg"
  ICON_LINE="Icon=tarlauncher"
elif [ -f "${SRC_DIR}/icon.png" ]; then
  cp "${SRC_DIR}/icon.png" "${ICON_DIR}/tarlauncher.png"
  ICON_LINE="Icon=tarlauncher"
fi

cat > "${APPS_DIR}/gearleverfortar.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=${APP_NAME}
Comment=Tar-Archive & Verzeichnisse installieren, verwalten, aktualisieren
Exec=${INSTALL_DIR}/main.py
${ICON_LINE}
Categories=Utility;System;
Terminal=false
StartupNotify=true
EOF

# Desktop-Datenbank aktualisieren
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPS_DIR}" || true
fi

echo "Fertig. Die App erscheint im Anwendungsmenü."
echo "Starten mit: ${INSTALL_DIR}/main.py"