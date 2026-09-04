#!/usr/bin/env python3
"""
revertir-flecha-combo.py

Revierte arreglar-flecha-combo.py: algo en esa regla (el boton del
combo box) rompio la pantalla inicial ("Como quieres entrar?"), asi
que se deshace ese ultimo cambio y se vuelve al estado de justo antes
(donde solo quedaba blanca la esquinita del combo, un detalle menor).

Uso: parado en la raiz del repo:
    python3 revertir-flecha-combo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
BACKUP = ARCHIVO + ".bak21"


def main():
    try:
        with open(BACKUP, "r", encoding="utf-8"):
            pass
    except FileNotFoundError:
        print(f"ERROR: no se encontro {BACKUP}.")
        print("       Este backup lo crea arreglar-flecha-combo.py justo antes de aplicarse;")
        print("       si no esta, no se puede revertir automaticamente asi.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak22-antes-de-revertir")
    print(f"Backup del estado actual (por si acaso): {ARCHIVO}.bak22-antes-de-revertir")

    shutil.copy(BACKUP, ARCHIVO)
    print(f"{ARCHIVO} restaurado al estado anterior a arreglar-flecha-combo.py.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
