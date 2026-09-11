#!/usr/bin/env python3
"""
aplanar-botones-barra-titulo.py

Los botones de la barra de titulo propia (restaurar/maximizar y cerrar)
se veian como cuadritos con fondo solido, porque heredaban el estilo
general de "boton" (fondo blanco/gris + borde). Se les da el estilo
plano/transparente tipico de una barra de titulo: sin fondo, sin borde,
y un resaltado suave solo al pasar el mouse.

No cambia ningun otro boton de la app -- solo los que estan dentro de
una barra de titulo (headerbar).

Uso: parado en la raiz del repo:
    python3 aplanar-botones-barra-titulo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        ".pawos-fondo-transparente {"
        "  background-color: transparent;"
        "  background-image: none;"
        "}"
'''
NUEVO = '''        ".pawos-fondo-transparente {"
        "  background-color: transparent;"
        "  background-image: none;"
        "}"
        /* Botones de la barra de titulo propia (maximizar/restaurar,
         * cerrar): planos, sin el fondo solido de los botones normales. */
        "headerbar button, .titlebar button, decoration button {"
        "  background-color: transparent;"
        "  background-image: none;"
        "  border: none;"
        "  box-shadow: none;"
        "  padding: 6px;"
        "}"
        "headerbar button:hover, .titlebar button:hover, decoration button:hover {"
        "  background-color: rgba(255,255,255,0.15);"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak22")
    print(f"Backup creado: {ARCHIVO}.bak22")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: botones de la barra de titulo ahora son planos.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
