#!/bin/sh
# Construit un .deb local simple sans accès réseau.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD="$ROOT/packaging/build"
rm -rf "$BUILD"
mkdir -p "$BUILD/DEBIAN" "$BUILD/usr/share/clavia/src" "$BUILD/usr/share/clavia/assets" \
         "$BUILD/usr/bin" "$BUILD/usr/share/applications" "$BUILD/usr/share/icons/hicolor/scalable/apps"
cp "$ROOT"/src/*.py "$BUILD/usr/share/clavia/src/"
cp "$ROOT/assets/style.css" "$ROOT/assets/style-light.css" "$ROOT/assets/flamme-streak.png" "$BUILD/usr/share/clavia/assets/"
mkdir -p "$BUILD/usr/share/clavia/assets/sounds"
cp "$ROOT"/assets/sounds/*.wav "$BUILD/usr/share/clavia/assets/sounds/"
cp "$ROOT/assets/clavia.svg" "$BUILD/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT/packaging/clavia.desktop" "$BUILD/usr/share/applications/"
cat > "$BUILD/usr/bin/clavia" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/clavia/src/main.py "$@"
EOF
chmod 755 "$BUILD/usr/bin/clavia"
cat > "$BUILD/DEBIAN/control" <<'EOF'
Package: clavia
Version: 3.5.4
Architecture: all
Maintainer: Clavia Contributors <noreply@example.invalid>
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, pulseaudio-utils
Description: Clavia Dark Slate, jeu educatif AZERTY hors ligne
 Application GTK4 pour apprendre a taper mots, phrases et textes.
EOF
chmod 755 "$BUILD/DEBIAN"
chmod g-s "$BUILD/DEBIAN"
dpkg-deb --build --root-owner-group "$BUILD" "$ROOT/clavia_3.5.4_all.deb"
printf 'Paquet créé : %s/clavia_3.5.4_all.deb\n' "$ROOT"
