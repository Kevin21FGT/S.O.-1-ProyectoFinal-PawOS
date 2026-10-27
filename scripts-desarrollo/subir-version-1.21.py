#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subir-version-1.21.py

Sube PAWOS_VERSION de "1.20" a "1.21" en include/version.h.
Sigue el mismo patron que subir-version-1.20.py.

Uso: parado en la raiz del repo:
    python3 subir-version-1.21.py
"""
import shutil
import sys
from pathlib import Path

VERSION_H = Path("include/version.h")

ANCLA = '#define PAWOS_VERSION "1.20"'
NUEVO = '#define PAWOS_VERSION "1.21"'


def main():
    if not VERSION_H.exists():
        print(f"ERROR: no se encontro {VERSION_H}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = VERSION_H.read_text(encoding="utf-8")
    if ANCLA not in contenido:
        print("ERROR: no se encontro la version 1.20 esperada en include/version.h.")
        print("       (puede que ya este en otra version)")
        sys.exit(1)

    backup = VERSION_H.with_suffix(".h.bak14")
    shutil.copy(VERSION_H, backup)
    contenido = contenido.replace(ANCLA, NUEVO, 1)
    VERSION_H.write_text(contenido, encoding="utf-8")

    print(f"  {VERSION_H}: version actualizada a 1.21. Respaldo en {backup}")


if __name__ == "__main__":
    main()
