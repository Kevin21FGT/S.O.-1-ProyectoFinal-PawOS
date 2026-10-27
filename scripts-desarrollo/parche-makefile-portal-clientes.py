#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-makefile-portal-clientes.py

Agrega el target "portal-clientes" al Makefile para compilar la nueva
app PawOS Portal de Clientes (src/main_portal_clientes.c), siguiendo
el mismo patron que "gui" y "vacunas-gui" (si usa la base de datos,
lleva -lsqlite3 -lm -lcrypt -lodbc).

IMPORTANTE: antes de correr esto, copia main_portal_clientes.c a
src/main_portal_clientes.c, y asegurate de haber corrido ya
parche-makefile-monitor-gui.py (este parche se ancla justo despues de
ese target).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-makefile-portal-clientes.py
"""
import shutil
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

ANCLA_VAR = "MONITOR_GUI_BIN = pawos-monitor-gui\n"
NUEVO_VAR = "MONITOR_GUI_BIN = pawos-monitor-gui\nPORTAL_CLIENTES_BIN = pawos-portal-clientes\n"

ANCLA_TARGET = "clean-monitor-gui:\n\trm -f $(MONITOR_GUI_BIN)\n"
NUEVO_TARGET = (
    "clean-monitor-gui:\n"
    "\trm -f $(MONITOR_GUI_BIN)\n"
    "\n"
    "portal-clientes: src/main_portal_clientes.c src/db/db.c\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_portal_clientes.c src/db/db.c -o $(PORTAL_CLIENTES_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt -lodbc\n"
    "\n"
    "clean-portal-clientes:\n"
    "\trm -f $(PORTAL_CLIENTES_BIN)\n"
)


def main():
    if not MAKEFILE.exists():
        print("ERROR: no se encontro Makefile. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if not Path("src/main_portal_clientes.c").exists():
        print("ERROR: no se encontro src/main_portal_clientes.c.")
        print("       Copia primero main_portal_clientes.c a src/main_portal_clientes.c")
        sys.exit(1)

    contenido = MAKEFILE.read_text(encoding="utf-8")

    for nombre, ancla in (("variable PORTAL_CLIENTES_BIN", ANCLA_VAR), ("target clean-monitor-gui", ANCLA_TARGET)):
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en Makefile.")
            print("       (corre primero parche-makefile-monitor-gui.py, o puede que esto ya este parchado)")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar.")
            sys.exit(1)

    backup = MAKEFILE.with_suffix(".bak_portal_clientes")
    shutil.copy(MAKEFILE, backup)

    contenido = contenido.replace(ANCLA_VAR, NUEVO_VAR, 1)
    contenido = contenido.replace(ANCLA_TARGET, NUEVO_TARGET, 1)
    MAKEFILE.write_text(contenido, encoding="utf-8")

    print(f"  Makefile: se agrego el target 'portal-clientes' (y 'clean-portal-clientes'). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make portal-clientes")
    print("  ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
