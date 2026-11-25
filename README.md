# Gear Lever for Tar

Eine kleine Desktop-App (Python + GTK4), um `tar.gz`/`tgz`/`tar`-Archive als
Anwendungen zu installieren, zu verwalten, zu verschieben und zu deinstallieren.

## Funktionen

- **Installieren**: tar.gz auswählen, Zielverzeichnis wählen, Name und
  Startdatei festlegen.
- **Verwalten**: Liste aller installierten Apps mit Pfad.
- **Verschieben**: Installationsordner an einen anderen Ort bewegen
  (Pfad wird automatisch aktualisiert).
- **Öffnen**: Startet die App bzw. öffnet den Ordner.
- **Deinstallieren**: Löscht Ordner und Registry-Eintrag.

Daten werden in `~/.local/share/gearleverfortar/apps.json` gespeichert.

## Start

```bash
./main.py
```

Benötigt: Python 3, PyGObject, GTK4, libadwaita.
EOF
echo done