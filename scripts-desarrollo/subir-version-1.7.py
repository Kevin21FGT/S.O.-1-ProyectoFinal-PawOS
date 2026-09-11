#!/usr/bin/env python3
"""
subir-version-1.7.py

Sube el numero de version de PawOS Refugio de 1.6 a 1.7 en
include/version.h.

Uso: parado en la raiz del repo:
    python3 subir-version-1.7.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.6"'
NUEVO = '#define PAWOS_VERSION "1.7"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la linea de version esperada.")
        print("       Puede que la version ya no sea 1.6, o que el archivo ya haya sido modificado.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak5")
    print(f"Backup creado: {ARCHIVO}.bak5")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: version 1.6 -> 1.7")
    print("")
    print("Ahora corre:  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
