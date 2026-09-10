#!/usr/bin/env python3
"""
oscurecer-fondo-colaborador.py

La imagen de oficina del login de Colaborador es mas clara que la del
bosque, y el texto blanco (Usuario/Contrasena) no se leia bien encima.
Se sube la opacidad del tinte verde oscuro que va sobre la imagen.

Uso: parado en la raiz del repo:
    python3 oscurecer-fondo-colaborador.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        ".pawos-fondo-colaborador {"
        "  background-image: linear-gradient(rgba(14,61,30,0.55), rgba(18,69,31,0.55)), url(\\"%s\\");"
'''
NUEVO = '''        ".pawos-fondo-colaborador {"
        "  background-image: linear-gradient(rgba(10,46,22,0.8), rgba(12,51,24,0.8)), url(\\"%s\\");"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak27")
    print(f"Backup creado: {ARCHIVO}.bak27")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: fondo del login de Colaborador mas oscuro.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
