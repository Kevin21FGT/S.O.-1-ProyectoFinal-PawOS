#!/usr/bin/env python3
"""
subir-version-1.2.py

Sube la version de PawOS Refugio de 1.1 a 1.2 en include/version.h,
por el nuevo dialogo de novedades agregado al buscar actualizaciones.

Uso: parado en la raiz del repo (rama-Combinada actualizada):
    python3 subir-version-1.2.py

Hace backup automatico a include/version.h.bak antes de tocar nada, y
aborta sin cambiar nada si no encuentra el texto exacto esperado.
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.1"'
NUEVO = '#define PAWOS_VERSION "1.2"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la linea exacta")
        print(f'       {ANCLA!r} en {ARCHIVO}.')
        print("       Puede que la version ya haya cambiado. No se toco nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak")
    print(f"Backup creado: {ARCHIVO}.bak")

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} actualizado a version 1.2 OK.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
