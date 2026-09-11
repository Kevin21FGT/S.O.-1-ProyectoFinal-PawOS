#!/usr/bin/env python3
"""
subir-version-1.9.py

Sube la version de PawOS de 1.8 a 1.9 (se agrega la copia de los 5
scripts de recordatorio de citas a instalar-pawos.sh y
construir-deb.sh, para que una instalacion nueva desde cero los deje
listos en /usr/local/bin).

Uso: parado en la raiz del repo:
    python3 subir-version-1.9.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.8"'
NUEVO = '#define PAWOS_VERSION "1.9"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) '{ANCLA}' en {ARCHIVO}.")
        print("       Puede que la version actual ya no sea 1.8. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak2")
    print(f"Backup creado: {ARCHIVO}.bak2")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.8 -> 1.9.")

    print("")
    print("Ahora recompila y confirma que el banner muestre 1.9:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")


if __name__ == "__main__":
    main()
