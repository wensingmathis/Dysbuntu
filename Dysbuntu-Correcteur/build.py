#!/usr/bin/env python3
"""Construit dist/dysbuntu-correcteur-<version>.oxt (une archive ZIP) avec la bibliothèque standard."""
import os
import sys
import zipfile
import xml.dom.minidom

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "extension")
DIST = os.path.join(ROOT, "dist")


def version() -> str:
    doc = xml.dom.minidom.parse(os.path.join(SRC, "description.xml"))
    return doc.getElementsByTagName("version")[0].getAttribute("value")


def iter_files():
    for base, dirs, files in os.walk(SRC):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo")) or name.startswith("."):
                continue
            full = os.path.join(base, name)
            yield full, os.path.relpath(full, SRC).replace(os.sep, "/")


def check_xml():
    for full, rel in iter_files():
        if rel.endswith((".xml", ".xcu")):
            xml.dom.minidom.parse(full)  # lève une exception si mal formé


def build() -> str:
    check_xml()
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "dysbuntu-correcteur-%s.oxt" % version())
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in iter_files():
            zf.write(full, rel)
    return out


if __name__ == "__main__":
    path = build()
    print(path)
    sys.exit(0)
