#!/usr/bin/env python3
"""
agrandar-texto-bienvenida.py

Agranda el texto "Bienvenid@ a PawOS" en la barra de bienvenida del
selector inicial.

Uso: parado en la raiz del repo:
    python3 agrandar-texto-bienvenida.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        "<span size='x-large' weight='bold'>Bienvenid@ a PawOS</span>");
'''
NUEVO = '''        "<span size='xx-large' weight='bold'>Bienvenid@ a PawOS</span>");
'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque esperado se encontro {n} veces (se esperaba 1). No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak20")
    print(f"Backup creado: {ARCHIVO}.bak20")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: texto de bienvenida mas grande.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
