#!/usr/bin/env python3
"""
achicar-botones-barra-titulo.py

Los botones de la barra de titulo (maximizar/restaurar y cerrar) se
ven un poco grandes. Se les reduce el padding y el tamano minimo.

Uso: parado en la raiz del repo:
    python3 achicar-botones-barra-titulo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        "headerbar button, .titlebar button, decoration button {"
        "  background-color: transparent;"
        "  background-image: none;"
        "  border: none;"
        "  box-shadow: none;"
        "  padding: 6px;"
        "}"
'''
NUEVO = '''        "headerbar button, .titlebar button, decoration button {"
        "  background-color: transparent;"
        "  background-image: none;"
        "  border: none;"
        "  box-shadow: none;"
        "  padding: 2px;"
        "  min-width: 22px;"
        "  min-height: 22px;"
        "}"
        ".pawos-boton-cerrar-barra {"
        "  font-size: 13px;"
        "  padding: 0px 6px;"
        "}"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak25")
    print(f"Backup creado: {ARCHIVO}.bak25")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: botones de la barra de titulo mas chicos.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
