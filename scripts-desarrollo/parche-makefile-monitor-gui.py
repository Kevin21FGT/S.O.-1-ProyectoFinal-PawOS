#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-makefile-monitor-gui.py

Agrega el target "monitor-gui" al Makefile para compilar la nueva app
PawOS Monitor (src/main_monitor_gui.c), siguiendo el mismo patron que
"gui" y "vacunas-gui".

IMPORTANTE: antes de correr esto, copia main_monitor_gui.c a
src/main_monitor_gui.c, y asegurate de haber corrido ya
parche-makefile-vacunas-gui.py (este parche depende de que el target
"vacunas-gui" ya exista en el Makefile, para anclarse justo despues).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-makefile-monitor-gui.py
"""
import shutil
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

ANCLA_VAR = "VACUNAS_GUI_BIN = pawos-vacunas-gui\n"
NUEVO_VAR = "VACUNAS_GUI_BIN = pawos-vacunas-gui\nMONITOR_GUI_BIN = pawos-monitor-gui\n"

ANCLA_TARGET = "clean-vacunas-gui:\n\trm -f $(VACUNAS_GUI_BIN)\n"
NUEVO_TARGET = (
    "clean-vacunas-gui:\n"
    "\trm -f $(VACUNAS_GUI_BIN)\n"
    "\n"
    "monitor-gui: src/main_monitor_gui.c src/db/db.c\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_monitor_gui.c src/db/db.c -o $(MONITOR_GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt -lodbc\n"
    "\n"
    "clean-monitor-gui:\n"
    "\trm -f $(MONITOR_GUI_BIN)\n"
)


def main():
    if not MAKEFILE.exists():
        print("ERROR: no se encontro Makefile. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if not Path("src/main_monitor_gui.c").exists():
        print("ERROR: no se encontro src/main_monitor_gui.c.")
        print("       Copia primero main_monitor_gui.c a src/main_monitor_gui.c")
        sys.exit(1)

    contenido = MAKEFILE.read_text(encoding="utf-8")

    for nombre, ancla in (("variable MONITOR_GUI_BIN", ANCLA_VAR), ("target clean-vacunas-gui", ANCLA_TARGET)):
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en Makefile.")
            print("       (corre primero parche-makefile-vacunas-gui.py, o puede que esto ya este parchado)")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar.")
            sys.exit(1)

    backup = MAKEFILE.with_suffix(".bak_monitor_gui")
    shutil.copy(MAKEFILE, backup)

    contenido = contenido.replace(ANCLA_VAR, NUEVO_VAR, 1)
    contenido = contenido.replace(ANCLA_TARGET, NUEVO_TARGET, 1)
    MAKEFILE.write_text(contenido, encoding="utf-8")

    print(f"  Makefile: se agrego el target 'monitor-gui' (y 'clean-monitor-gui'). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make monitor-gui")
    print("  ./pawos-monitor-gui")


if __name__ == "__main__":
    main()
