#!/usr/bin/env python3
"""
subir-version-1.3.py

Sube el numero de version de PawOS Refugio de 1.2 a 1.3 en
include/version.h.

Uso: parado en la raiz del repo:
    python3 subir-version-1.3.py

Hace backup (.bak) antes de tocar nada, y aborta sin cambiar nada si
el texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.2"'
NUEVO = '#define PAWOS_VERSION "1.3"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la linea de version esperada.")
        print("       Puede que la version ya no sea 1.2, o que el archivo ya haya sido modificado.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak")
    print(f"Backup creado: {ARCHIVO}.bak")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: version 1.2 -> 1.3")
    print("")
    print("Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
