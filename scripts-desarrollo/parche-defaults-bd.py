#!/usr/bin/env python3
"""
parche-defaults-bd.py

Cambia los valores POR DEFECTO de la conexion a SQL Server (los que se usan
si no existe ~/.pawos_db_config) de la cuenta vieja y suspendida
(sql5111 / db_ace27e_pawos) a la cuenta de paga:

    servidor: sql8011.site4now.net
    base:     db_acf53d_pawos
    usuario:  db_acf53d_pawos_admin

La contrasena NO esta en el codigo: sigue en ~/.pawos_db_remota.

Uso (parado en la raiz del repo):
    python3 parche-defaults-bd.py
    make   &&   make gui portal-clientes archivos-gui vacunas-gui
"""

import shutil
import sys

ARCHIVO = "src/db/db.c"

CAMBIOS = [
    ('#define API_SQL_SERVIDOR  "sql5111.site4now.net"',
     '#define API_SQL_SERVIDOR  "sql8011.site4now.net"', "servidor"),
    ('#define API_SQL_BASE      "db_ace27e_pawos"',
     '#define API_SQL_BASE      "db_acf53d_pawos"', "base"),
    ('#define API_SQL_USUARIO   "db_ace27e_pawos_admin"',
     '#define API_SQL_USUARIO   "db_acf53d_pawos_admin"', "usuario"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "sql8011.site4now.net" in contenido and "sql5111.site4now.net" not in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_defaults_bd")
    print(f"Backup: {ARCHIVO}.bak_defaults_bd")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: valores por defecto ahora apuntan a sql8011 / db_acf53d_pawos.")
    print("Compila todo:  make && make gui portal-clientes archivos-gui vacunas-gui")


if __name__ == "__main__":
    main()
