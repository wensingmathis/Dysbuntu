#!/bin/sh
# Offline, isolated Debian package build; never modifies the original source.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v dpkg-deb >/dev/null 2>&1 || { echo 'dpkg-deb manquant' >&2; exit 1; }
BUILD=$(mktemp -d "$ROOT/packaging/.build.XXXXXXXX")
trap 'rm -rf -- "$BUILD"' EXIT HUP INT TERM
install -d "$BUILD/DEBIAN" "$BUILD/usr/share/clavia/src" \
    "$BUILD/usr/share/clavia/assets/sounds" \
    "$BUILD/usr/share/clavia/assets/backgrounds" "$BUILD/usr/bin" \
    "$BUILD/usr/share/applications" \
    "$BUILD/usr/share/doc/clavia" \
    "$BUILD/usr/share/icons/hicolor/scalable/apps"
cp "$ROOT"/src/*.py "$BUILD/usr/share/clavia/src/"
cp "$ROOT/assets/style.css" "$ROOT/assets/style-light.css" \
   "$ROOT/assets/flamme-streak.png" "$BUILD/usr/share/clavia/assets/"
cp "$ROOT"/assets/backgrounds/*.png "$BUILD/usr/share/clavia/assets/backgrounds/"
cp "$ROOT"/assets/sounds/*.wav "$BUILD/usr/share/clavia/assets/sounds/"
cp "$ROOT/README.md" "$ROOT/AUDIT.md" "$ROOT/LICENSE" \
   "$ROOT/assets/sounds/README-LICENCES.txt" "$BUILD/usr/share/doc/clavia/"
cp "$ROOT/assets/clavia.svg" "$BUILD/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT/packaging/clavia.desktop" "$BUILD/usr/share/applications/"
cat > "$BUILD/usr/bin/clavia" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/share/clavia/src/main.py "$@"
EOF
chmod 755 "$BUILD/usr/bin/clavia"
cat > "$BUILD/DEBIAN/control" <<'EOF'
Package: clavia
Version: 3.5.7
Architecture: all
Maintainer: Mathis Wensing
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, pulseaudio-utils
Description: Clavia - jeu educatif AZERTY hors ligne
 Application GTK4 pour apprendre a taper des mots, phrases et textes.
EOF
dpkg-deb --build --root-owner-group "$BUILD" "$ROOT/clavia_3.5.7_all.deb"
printf 'Paquet créé : %s/clavia_3.5.7_all.deb\n' "$ROOT"
