#!/usr/bin/env python3
"""
parche-reconectar-ping.py   (refuerza parche-reconectar-bd.py)

Problema: a veces TODAS las listas fallan ("No se pudo leer la lista...")
aunque la red y la base funcionan: el programa reutiliza una conexion que el
servidor ya cerro, y FreeTDS no siempre lo reporta con SQL_ATTR_CONNECTION_DEAD.

Solucion: si la conexion guardada lleva mas de 10 s sin usarse, se le manda
un "SELECT 1" de prueba (un viaje de ~30 ms). Si falla, se descarta y se abre
una conexion nueva. Tambien avisa en la terminal: "[PawOS] conexion a la BD
perdida, reconectando...".

Uso (parado en la raiz del repo):
    python3 parche-reconectar-ping.py
    make gui
"""

import shutil
import sys

DB_C = "src/db/db.c"

ANCLA = r"""        SQLUINTEGER conexion_muerta = SQL_CD_FALSE;
        if (SQL_SUCCEEDED(SQLGetConnectAttr(g_hdbc_remoto, SQL_ATTR_CONNECTION_DEAD,
                                            &conexion_muerta, 0, NULL))
            && conexion_muerta == SQL_CD_TRUE) {
            api_cerrar_conexion_remota();
        }"""

NUEVO = r"""        SQLUINTEGER conexion_muerta = SQL_CD_FALSE;
        if (SQL_SUCCEEDED(SQLGetConnectAttr(g_hdbc_remoto, SQL_ATTR_CONNECTION_DEAD,
                                            &conexion_muerta, 0, NULL))
            && conexion_muerta == SQL_CD_TRUE) {
            api_cerrar_conexion_remota();
        } else if ((ahora - g_ultimo_uso_remoto) > 10) {
            /* Prueba barata: si no responde, la conexion guardada ya murio. */
            SQLHSTMT h_ping;
            int viva = 0;
            if (SQLAllocHandle(SQL_HANDLE_STMT, g_hdbc_remoto, &h_ping) == SQL_SUCCESS) {
                if (SQL_SUCCEEDED(SQLExecDirect(h_ping, (SQLCHAR *)"SELECT 1", SQL_NTS)))
                    viva = 1;
                SQLFreeHandle(SQL_HANDLE_STMT, h_ping);
            }
            if (!viva) {
                fprintf(stderr, "[PawOS] conexion a la BD perdida, reconectando...\n");
                api_cerrar_conexion_remota();
            }
        }"""


def main():
    try:
        with open(DB_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {DB_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "conexion a la BD perdida" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque a reforzar aparece {n} veces (debe ser 1). No se cambio nada.")
        print("       Verifica que ya aplicaste parche-reconectar-bd.py.")
        sys.exit(1)

    shutil.copy(DB_C, DB_C + ".bak_reconectar_ping")
    print(f"Backup: {DB_C}.bak_reconectar_ping")
    contenido = contenido.replace(ANCLA, NUEVO, 1)
    with open(DB_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{DB_C} parchado OK.")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
