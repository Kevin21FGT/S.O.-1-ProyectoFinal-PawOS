#!/usr/bin/env python3
"""
quitar-cuadro-boton-cerrar.py

El boton de "Restaurar" ya quedo plano, pero el de cerrar (X) seguia
con el cuadro de fondo gris. Es porque GTK le pone su propia clase
interna a ese boton especifico (".titlebutton"), que tiene mas
prioridad que la regla generica "headerbar button" que ya se agrego.
Este parche apunta directo a esa clase para quitarle tambien el fondo.

Uso: parado en la raiz del repo:
    python3 quitar-cuadro-boton-cerrar.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        "headerbar button:hover, .titlebar button:hover, decoration button:hover {"
        "  background-color: rgba(255,255,255,0.15);"
        "}"
'''
NUEVO = '''        "headerbar button:hover, .titlebar button:hover, decoration button:hover {"
        "  background-color: rgba(255,255,255,0.15);"
        "}"
        /* El boton de cerrar que GTK agrega solo trae su propia clase
         * interna (.titlebutton) que le gana en prioridad a la regla
         * de arriba -- se apunta directo a ella para quitarle el
         * cuadro de fondo tambien. */
        "headerbar .titlebutton, headerbar button.titlebutton {"
        "  background-color: transparent;"
        "  background-image: none;"
        "  border: none;"
        "  box-shadow: none;"
        "}"
        "headerbar .titlebutton:hover, headerbar button.titlebutton:hover {"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak23")
    print(f"Backup creado: {ARCHIVO}.bak23")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: boton de cerrar tambien plano.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
