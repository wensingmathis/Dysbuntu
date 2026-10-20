#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
cat > "$HOME/.local/bin/clavia" <<EOF
#!/bin/sh
exec /usr/bin/python3 "$ROOT/src/main.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/clavia"
sed "s|^Exec=.*|Exec=$HOME/.local/bin/clavia|" "$ROOT/packaging/clavia.desktop" > "$HOME/.local/share/applications/clavia.desktop"
cp "$ROOT/assets/clavia.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/clavia.svg"
printf 'Clavia installé dans le menu des applications.\n'
