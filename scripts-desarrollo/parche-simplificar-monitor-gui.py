#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-simplificar-monitor-gui.py

Ajusta el target "monitor-gui" del Makefile: la nueva version de
PawOS Monitor ya no usa la base de datos (se quito la seccion de
Alertas de Sensores, que ya se repetia con Refugio GUI), asi que ya
no necesita enlazar src/db/db.c ni -lsqlite3/-lm/-lcrypt/-lodbc.

IMPORTANTE: corre esto DESPUES de haber corrido ya
parche-makefile-monitor-gui.py (este parche solo ajusta ese target,
no lo crea).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-simplificar-monitor-gui.py
"""
import shutil
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

ANCLA = (
    "monitor-gui: src/main_monitor_gui.c src/db/db.c\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_monitor_gui.c src/db/db.c -o $(MONITOR_GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt -lodbc\n"
)
NUEVO = (
    "monitor-gui: src/main_monitor_gui.c\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_monitor_gui.c -o $(MONITOR_GUI_BIN) $(GTK_LIBS)\n"
)


def main():
    if not MAKEFILE.exists():
        print("ERROR: no se encontro Makefile. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = MAKEFILE.read_text(encoding="utf-8")

    apariciones = contenido.count(ANCLA)
    if apariciones == 0:
        print("ERROR: no se encontro el target 'monitor-gui' esperado en Makefile.")
        print("       (corre primero parche-makefile-monitor-gui.py, o puede que esto ya este parchado)")
        sys.exit(1)
    if apariciones > 1:
        print("ERROR: el ancla aparece mas de una vez, no es seguro parchar.")
        sys.exit(1)

    backup = MAKEFILE.with_suffix(".bak_simplificar_monitor_gui")
    shutil.copy(MAKEFILE, backup)

    contenido = contenido.replace(ANCLA, NUEVO, 1)
    MAKEFILE.write_text(contenido, encoding="utf-8")

    print(f"  Makefile: target 'monitor-gui' simplificado (ya no depende de db.c). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make clean-monitor-gui")
    print("  make monitor-gui")
    print("  ./pawos-monitor-gui")


if __name__ == "__main__":
    main()
