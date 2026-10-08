#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-makefile-archivos-gui.py

Agrega el target "archivos-gui" al Makefile para compilar la nueva app
PawOS Archivos (src/main_archivos_gui.c). Esta app reutiliza archivos.c
e integridad.c, y integridad.c necesita el checksum en Ensamblador
(checksum.asm), asi que el target ensambla checksum.o con nasm antes de
enlazar, igual que ya hace el target principal.

IMPORTANTE: antes de correr esto, copia main_archivos_gui.c a
src/main_archivos_gui.c, y asegurate de haber corrido ya
parche-makefile-portal-clientes.py (este parche se ancla justo despues
de ese target).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-makefile-archivos-gui.py
"""
import shutil
import sys
from pathlib import Path

MAKEFILE = Path("Makefile")

ANCLA_VAR = "PORTAL_CLIENTES_BIN = pawos-portal-clientes\n"
NUEVO_VAR = "PORTAL_CLIENTES_BIN = pawos-portal-clientes\nARCHIVOS_GUI_BIN = pawos-archivos-gui\n"

ANCLA_TARGET = "clean-portal-clientes:\n\trm -f $(PORTAL_CLIENTES_BIN)\n"
NUEVO_TARGET = (
    "clean-portal-clientes:\n"
    "\trm -f $(PORTAL_CLIENTES_BIN)\n"
    "\n"
    "archivos-gui: src/main_archivos_gui.c src/archivos/archivos.c src/integridad/integridad.c src/db/db.c src/integridad/checksum.asm\n"
    "\tnasm -f elf64 src/integridad/checksum.asm -o src/integridad/checksum.o\n"
    "\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_archivos_gui.c src/archivos/archivos.c src/integridad/integridad.c src/db/db.c src/integridad/checksum.o -o $(ARCHIVOS_GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt -lodbc\n"
    "\n"
    "clean-archivos-gui:\n"
    "\trm -f $(ARCHIVOS_GUI_BIN)\n"
)


def main():
    if not MAKEFILE.exists():
        print("ERROR: no se encontro Makefile. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if not Path("src/main_archivos_gui.c").exists():
        print("ERROR: no se encontro src/main_archivos_gui.c.")
        print("       Copia primero main_archivos_gui.c a src/main_archivos_gui.c")
        sys.exit(1)

    contenido = MAKEFILE.read_text(encoding="utf-8")

    for nombre, ancla in (("variable ARCHIVOS_GUI_BIN", ANCLA_VAR), ("target clean-portal-clientes", ANCLA_TARGET)):
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en Makefile.")
            print("       (corre primero parche-makefile-portal-clientes.py, o puede que esto ya este parchado)")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar.")
            sys.exit(1)

    backup = MAKEFILE.with_suffix(".bak_archivos_gui")
    shutil.copy(MAKEFILE, backup)

    contenido = contenido.replace(ANCLA_VAR, NUEVO_VAR, 1)
    contenido = contenido.replace(ANCLA_TARGET, NUEVO_TARGET, 1)
    MAKEFILE.write_text(contenido, encoding="utf-8")

    print(f"  Makefile: se agrego el target 'archivos-gui' (y 'clean-archivos-gui'). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make archivos-gui")
    print("  ./pawos-archivos-gui")


if __name__ == "__main__":
    main()
