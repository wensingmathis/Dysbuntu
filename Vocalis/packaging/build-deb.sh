#!/usr/bin/env bash
# Construire un paquet Debian hors ligne embarquant code + logo original.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$(pwd)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/DEBIAN" "$stage/usr/lib/vocalis" \
         "$stage/usr/bin" "$stage/usr/share/applications" \
         "$stage/usr/share/doc/dysbuntu-vocalis"
cp main.py diagnostic_piper.py Vocalis.jpeg "$stage/usr/lib/vocalis/"
cp -R tts ui "$stage/usr/lib/vocalis/"
find "$stage/usr/lib/vocalis" -type d -name __pycache__ -prune -exec rm -rf '{}' +
cp packaging/vocalis.desktop "$stage/usr/share/applications/vocalis.desktop"
cp README.md "$stage/usr/share/doc/dysbuntu-vocalis/README.md"
cat > "$stage/usr/bin/vocalis" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/vocalis/main.py "$@"
LAUNCHER
chmod 0755 "$stage/usr/bin/vocalis"
cat > "$stage/DEBIAN/control" <<'CONTROL'
Package: dysbuntu-vocalis
Version: 0.2.0-1
Section: education
Priority: optional
Architecture: all
Maintainer: Dysbuntu Project
Depends: python3 (>= 3.10), python3-tk, espeak-ng, alsa-utils
Description: Vocalis - lecteur vocal local (Piper en option)
 Logiciel de synthèse vocale hors ligne avec interface Tkinter.
 Toutes les sources applicatives sont incluses dans le paquet.
CONTROL
chmod -R go-w "$stage"
chmod 0755 "$stage"  # Ne jamais packager une racine / avec les droits 0700 de mktemp.
dpkg-deb --build --root-owner-group "$stage" "$root/../dysbuntu-vocalis_0.2.0-1_all.deb"
