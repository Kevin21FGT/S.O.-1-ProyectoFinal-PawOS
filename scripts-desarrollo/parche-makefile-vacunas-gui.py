#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-makefile-vacunas-gui.py

Agrega el target "vacunas-gui" al Makefile para compilar la nueva app
PawOS Vacunas GUI (src/main_vacunas_gui.c), siguiendo el mismo patron
que el target "gui" ya existente (mismas flags, mismo estilo).

No toca ningun target existente, solo agrega:
  - La variable VACUNAS_GUI_BIN
  - El target "vacunas-gui" (compila)
  - El target "clean-vacunas-gui" (limpia)

IMPORTANTE: antes de correr esto, copia main_vacunas_gui.c a
src/main_vacunas_gui.c (no a la raiz del repo).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-makefile-vacunas-gui.py
"""
import shutil
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

ANCLA_VAR = "GUI_PRODUCTO_BIN = pawos-refugio-gui-producto\n"
NUEVO_VAR = "GUI_PRODUCTO_BIN = pawos-refugio-gui-producto\nVACUNAS_GUI_BIN = pawos-vacunas-gui\n"

ANCLA_TARGET = "clean-gui:\n\trm -f $(GUI_BIN) $(GUI_PRODUCTO_BIN)\n"
NUEVO_TARGET = (
    "clean-gui:\n"
    "\trm -f $(GUI_BIN) $(GUI_PRODUCTO_BIN)\n"
    "\n"
    "vacunas-gui: src/main_vacunas_gui.c src/db/db.c\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_vacunas_gui.c src/db/db.c -o $(VACUNAS_GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt -lodbc\n"
    "\n"
    "clean-vacunas-gui:\n"
    "\trm -f $(VACUNAS_GUI_BIN)\n"
)


def main():
    if not MAKEFILE.exists():
        print("ERROR: no se encontro Makefile. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if not Path("src/main_vacunas_gui.c").exists():
        print("ERROR: no se encontro src/main_vacunas_gui.c.")
        print("       Copia primero main_vacunas_gui.c a src/main_vacunas_gui.c")
        sys.exit(1)

    contenido = MAKEFILE.read_text(encoding="utf-8")

    for nombre, ancla in (("variable VACUNAS_GUI_BIN", ANCLA_VAR), ("target clean-gui", ANCLA_TARGET)):
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en Makefile.")
            print("       (puede que ya este parchado, o el archivo cambio)")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar.")
            sys.exit(1)

    backup = MAKEFILE.with_suffix(".bak_vacunas_gui")
    shutil.copy(MAKEFILE, backup)

    contenido = contenido.replace(ANCLA_VAR, NUEVO_VAR, 1)
    contenido = contenido.replace(ANCLA_TARGET, NUEVO_TARGET, 1)
    MAKEFILE.write_text(contenido, encoding="utf-8")

    print(f"  Makefile: se agrego el target 'vacunas-gui' (y 'clean-vacunas-gui'). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make vacunas-gui")
    print("  ./pawos-vacunas-gui")


if __name__ == "__main__":
    main()
