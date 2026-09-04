#!/usr/bin/env python3
"""
subir-version-1.11.py

Sube la version de PawOS de 1.10 a 1.11: instalar-pawos.sh y el
postinst del .deb ahora instalan fpdf2 (python3-pip + pip3 install)
automaticamente, para que una instalacion nueva desde cero no falle
al generar el PDF de citas por falta de esa libreria.

Uso: parado en la raiz del repo:
    python3 subir-version-1.11.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.10"'
NUEVO = '#define PAWOS_VERSION "1.11"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) '{ANCLA}' en {ARCHIVO}.")
        print("       Puede que la version actual ya no sea 1.10. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak4")
    print(f"Backup creado: {ARCHIVO}.bak4")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.10 -> 1.11.")

    print("")
    print("Ahora recompila y confirma que el banner muestre 1.11:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")
    print("")
    print("Y ordena la raiz del repo (mueve los scripts de hoy a scripts-desarrollo/):")
    print("  git mv agregar-recordatorios-automaticos.py scripts-desarrollo/ 2>/dev/null || mv agregar-recordatorios-automaticos.py scripts-desarrollo/")
    print("  git mv agregar-fpdf2-instalador.py scripts-desarrollo/ 2>/dev/null || mv agregar-fpdf2-instalador.py scripts-desarrollo/")
    print("  git mv subir-version-1.10.py scripts-desarrollo/ 2>/dev/null || mv subir-version-1.10.py scripts-desarrollo/")
    print("  git mv subir-version-1.11.py scripts-desarrollo/ 2>/dev/null || mv subir-version-1.11.py scripts-desarrollo/")


if __name__ == "__main__":
    main()
