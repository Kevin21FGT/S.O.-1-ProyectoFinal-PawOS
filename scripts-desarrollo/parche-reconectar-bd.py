#!/usr/bin/env python3
"""
parche-reconectar-bd.py

Problema: db.c reutiliza UNA conexion abierta a SmarterASP. Si el servidor
(o la red) la cierra, esa conexion queda muerta y TODAS las listas fallan
("No se pudo leer la lista...") hasta cerrar y volver a abrir el programa.

Solucion (pequena, no cambia ninguna funcion de negocio): antes de reutilizar
la conexion guardada, se pregunta al driver si sigue viva
(SQL_ATTR_CONNECTION_DEAD). Si esta muerta, se cierra y api_conectar abre
una nueva automaticamente.

Uso (parado en la raiz del repo):
    python3 parche-reconectar-bd.py
    make gui
"""

import shutil
import sys

DB_C = "src/db/db.c"

ANCLA = r"""    if (g_hdbc_remoto != NULL) {
        g_ultimo_uso_remoto = ahora;
        *out_henv = g_henv_remoto;
        *out_hdbc = g_hdbc_remoto;
        return 0;
    }"""

NUEVO = r"""    if (g_hdbc_remoto != NULL) {
        /* Si el servidor cerro la conexion guardada, descartarla para
         * que se abra una nueva en vez de fallar en todas las consultas. */
        SQLUINTEGER conexion_muerta = SQL_CD_FALSE;
        if (SQL_SUCCEEDED(SQLGetConnectAttr(g_hdbc_remoto, SQL_ATTR_CONNECTION_DEAD,
                                            &conexion_muerta, 0, NULL))
            && conexion_muerta == SQL_CD_TRUE) {
            api_cerrar_conexion_remota();
        }
    }
    if (g_hdbc_remoto != NULL) {
        g_ultimo_uso_remoto = ahora;
        *out_henv = g_henv_remoto;
        *out_hdbc = g_hdbc_remoto;
        return 0;
    }"""


def main():
    try:
        with open(DB_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {DB_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "SQL_ATTR_CONNECTION_DEAD" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque de reutilizar conexion aparece {n} veces (debe ser 1). No se cambio nada.")
        sys.exit(1)

    shutil.copy(DB_C, DB_C + ".bak_reconectar")
    print(f"Backup: {DB_C}.bak_reconectar")
    contenido = contenido.replace(ANCLA, NUEVO, 1)
    with open(DB_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{DB_C} parchado OK.")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
