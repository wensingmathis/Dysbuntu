#!/usr/bin/env python3
"""Fabrique localement un .deb autonome, sans script d'installation réseau.

Exécuter depuis une copie des sources de NumDys :
    python3 packaging/build_deb.py
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

VERSION = "0.2.0-1"
ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dist" / f"numdys_{VERSION}_all.deb"
CONTROL = f"""Package: numdys
Version: {VERSION}
Section: education
Priority: optional
Architecture: all
Maintainer: Dysbuntu Project
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0
Conflicts: dysbuntu-numdys-online
Description: Calculatrice scientifique et graphique accessible pour Linux
 Application GTK 3 hors ligne avec moteurs de calcul et affichage OpenDyslexic
 lorsque la police est présente sur le système.
"""
DESKTOP = """[Desktop Entry]
Type=Application
Name=NumDys
Comment=Calculatrice scientifique et graphique accessible
Exec=/usr/bin/numdys
Icon=accessories-calculator
Terminal=false
Categories=Education;Science;
"""
LAUNCHER = """#!/usr/bin/python3
\"\"\"Lance les sources déjà installées par le paquet, sans réseau.\"\"\"
import sys
sys.path.insert(0, '/usr/lib/numdys')
from main import main
if __name__ == '__main__':
    sys.exit(main())
"""


def main() -> None:
    if not shutil.which("dpkg-deb"):
        raise SystemExit("Erreur : dpkg-deb est nécessaire pour créer le paquet.")
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="numdys-deb-") as temporary:
        staging = Path(temporary) / "pkg"
        (staging / "DEBIAN").mkdir(parents=True)
        libdir = staging / "usr/lib/numdys"
        (libdir / "numdys").mkdir(parents=True)
        (staging / "usr/bin").mkdir(parents=True)
        desktop_dir = staging / "usr/share/applications"
        desktop_dir.mkdir(parents=True)
        (staging / "DEBIAN/control").write_text(CONTROL, encoding="utf-8")
        (desktop_dir / "numdys.desktop").write_text(DESKTOP, encoding="utf-8")
        shutil.copy2(ROOT / "main.py", libdir / "main.py")
        for source in (ROOT / "numdys").glob("*.py"):
            shutil.copy2(source, libdir / "numdys" / source.name)
        launcher = staging / "usr/bin/numdys"
        launcher.write_text(LAUNCHER, encoding="utf-8")
        launcher.chmod(0o755)
        # aucun maintainer script, aucun téléchargement, aucun appel à git.
        subprocess.run(
            ["dpkg-deb", "--build", "--root-owner-group", str(staging), str(DESTINATION)],
            check=True, timeout=60,
        )
    print(f"Paquet créé : {DESTINATION}")


if __name__ == "__main__":
    main()
