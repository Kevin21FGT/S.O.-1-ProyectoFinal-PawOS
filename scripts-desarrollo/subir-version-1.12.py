#!/usr/bin/env python3
"""
subir-version-1.12.py

Sube PAWOS_VERSION de 1.11 a 1.12 (icono de mostrar/ocultar contrasena
en los 9 campos de contrasena de la app).

Uso: parado en la raiz del repo:
    python3 subir-version-1.12.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.11"'
NUEVO = '#define PAWOS_VERSION "1.12"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro la version 1.11 esperada en version.h. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak5")
    print(f"Backup creado: {ARCHIVO}.bak5")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.11 -> 1.12.")

    print("")
    print("Ahora recompila y confirma que el banner muestre 1.12:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")
    print("")
    print("Y ordena la raiz del repo (mueve los scripts de hoy a scripts-desarrollo/):")
    print("  git mv agregar-icono-ver-password.py scripts-desarrollo/ 2>/dev/null || mv agregar-icono-ver-password.py scripts-desarrollo/")
    print("  git mv subir-version-1.12.py scripts-desarrollo/ 2>/dev/null || mv subir-version-1.12.py scripts-desarrollo/")


if __name__ == "__main__":
    main()
