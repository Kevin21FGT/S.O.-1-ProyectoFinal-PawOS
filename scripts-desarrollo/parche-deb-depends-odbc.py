#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-deb-depends-odbc.py

Agrega "unixodbc, tdsodbc" a la lista de Depends del paquete .deb
(dentro de construir-deb.sh), para que apt instale automaticamente
esas dos librerias en la maquina de quien instale pawos-refugio.deb
(necesarias porque el modulo de Gestion de Mascotas ahora se conecta
a SQL Server via ODBC/FreeTDS).

No hace falta tocar el compilado (construir-deb.sh ya usa "make gui",
que ya trae -lodbc agregado al Makefile).

Uso: parado en la raiz del repo:
    python3 parche-deb-depends-odbc.py
"""
import shutil
import sys
from pathlib import Path

SCRIPT = Path("construir-deb.sh")

ANCLA = "Depends: libgtk-3-0, libsqlite3-0, libncurses6, libcrypt1, python3, python3-pip, ufw, rclone"
NUEVO = "Depends: libgtk-3-0, libsqlite3-0, libncurses6, libcrypt1, unixodbc, tdsodbc, python3, python3-pip, ufw, rclone"


def main():
    if not SCRIPT.exists():
        print(f"ERROR: no se encontro {SCRIPT}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = SCRIPT.read_text(encoding="utf-8")
    if ANCLA not in contenido:
        print("ERROR: no se encontro la linea de Depends esperada en construir-deb.sh.")
        print("       (puede que ya este parchado)")
        sys.exit(1)

    backup = SCRIPT.with_suffix(".sh.bak_odbc")
    shutil.copy(SCRIPT, backup)
    contenido = contenido.replace(ANCLA, NUEVO, 1)
    SCRIPT.write_text(contenido, encoding="utf-8")

    print(f"  {SCRIPT}: Depends actualizado (se agrego unixodbc, tdsodbc). Respaldo en {backup}")


if __name__ == "__main__":
    main()
