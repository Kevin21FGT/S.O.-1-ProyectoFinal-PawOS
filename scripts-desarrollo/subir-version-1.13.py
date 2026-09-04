#!/usr/bin/env python3
"""
subir-version-1.13.py

Sube PAWOS_VERSION de 1.12 a 1.13: fundido al abrir ventanas/dialogos,
icono de la app, dialogo "Acerca de" y spinner en "Buscando
actualizaciones".

Uso: parado en la raiz del repo:
    python3 subir-version-1.13.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.12"'
NUEVO = '#define PAWOS_VERSION "1.13"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro la version 1.12 esperada en version.h. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak6")
    print(f"Backup creado: {ARCHIVO}.bak6")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.12 -> 1.13.")

    print("")
    print("Ahora recompila y confirma que el banner (y 'Acerca de') muestren 1.13:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")
    print("")
    print("Y ordena la raiz del repo (mueve los scripts de esta tanda y la anterior,")
    print("que quedaron sueltos, a scripts-desarrollo/):")
    for nombre in [
        "agregar-icono-ver-password.py",
        "subir-version-1.12.py",
        "agregar-transicion-campos.py",
        "agregar-fundido-ventanas.py",
        "arreglar-declaracion-fundido.py",
        "agregar-icono-app.py",
        "agregar-acerca-de.py",
        "agregar-spinner-buscando.py",
        "subir-version-1.13.py",
    ]:
        print(f"  git mv {nombre} scripts-desarrollo/ 2>/dev/null || mv {nombre} scripts-desarrollo/")


if __name__ == "__main__":
    main()
