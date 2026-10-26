#!/bin/sh
# Installs a standalone copy in the user's HOME without root permissions.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET="$HOME/.local/share/clavia"
install -d -m 700 "$TARGET" "$TARGET/src" "$TARGET/assets" \
    "$HOME/.local/bin" "$HOME/.local/share/applications" \
    "$HOME/.local/share/icons/hicolor/scalable/apps"
cp "$ROOT"/src/*.py "$TARGET/src/"
cp "$ROOT/assets/style.css" "$ROOT/assets/style-light.css" \
   "$ROOT/assets/flamme-streak.png" "$TARGET/assets/"
install -d "$TARGET/assets/sounds" "$TARGET/assets/backgrounds"
cp "$ROOT"/assets/sounds/*.wav "$TARGET/assets/sounds/"
cp "$ROOT"/assets/backgrounds/*.png "$TARGET/assets/backgrounds/"
cat > "$HOME/.local/bin/clavia" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 "$HOME/.local/share/clavia/src/main.py" "$@"
EOF
chmod 755 "$HOME/.local/bin/clavia"
cp "$ROOT/packaging/clavia.desktop" "$HOME/.local/share/applications/clavia.desktop"
cp "$ROOT/assets/clavia.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/clavia.svg"
printf 'Clavia est installé dans %s\n' "$TARGET"
printf 'Lance Clavia depuis le menu ou via ~/.local/bin/clavia\n'
