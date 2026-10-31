#!/usr/bin/env python3
"""
oscurecer-fondo-clientes.py

Sube el tinte oscuro sobre la imagen del bosque (selector, login y
registro de clientes, menu principal) un poco mas, igual que se hizo
con la imagen de oficina del login de Colaborador, para mas seguridad
de contraste en el texto.

Uso: parado en la raiz del repo:
    python3 oscurecer-fondo-clientes.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        ".pawos-fondo-dinamico {"
        "  background-image: linear-gradient(rgba(14,61,30,0.55), rgba(18,69,31,0.55)), url(\\"%s\\");"
'''
NUEVO = '''        ".pawos-fondo-dinamico {"
        "  background-image: linear-gradient(rgba(10,48,23,0.72), rgba(12,53,25,0.72)), url(\\"%s\\");"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak28")
    print(f"Backup creado: {ARCHIVO}.bak28")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: fondo del bosque un poco mas oscuro (selector, login/registro de clientes, menu).")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
