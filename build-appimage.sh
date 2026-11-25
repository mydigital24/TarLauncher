#!/usr/bin/env bash
set -e
APPDIR=/tmp/gearleverfortar-AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin/gearleverfortar"
cp -r . "$APPDIR/usr/bin/gearleverfortar/"
rm -rf "$APPDIR/usr/bin/gearleverfortar/__pycache__"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
exec python3 "${HERE}/usr/bin/gearleverfortar/main.py" "$@"
EOF
chmod +x "$APPDIR/AppRun"
cat > "$APPDIR/gearleverfortar.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Gear Lever for Tar
Exec=GearLeverForTar
Icon=tarlauncher
Categories=Utility;System;
Terminal=false
EOF
cp tarlauncher.svg "$APPDIR/tarlauncher.svg" 2>/dev/null || true
mkdir -p "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps"
cp "$APPDIR/gearleverfortar.desktop" "$APPDIR/usr/share/applications/"
cp "$APPDIR/tarlauncher.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/tarlauncher.svg" 2>/dev/null || true
ARCH=x86_64 /tmp/opencode/appimagetool "$APPDIR" TarLauncher-x86_64.AppImage
echo "Erstellt: TarLauncher-x86_64.AppImage"