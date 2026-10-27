#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-optimizar-conexion-persistente.py

Por que se "traba un cacho" PawOS ahora: cada vez que una pantalla
llama a una funcion mascota_*/vacuna_*/adopcion_*/donante_*/alerta_*,
esa funcion abre una conexion ODBC NUEVA por internet hacia el SQL
Server de SmarterASP (handshake TCP + login) y la cierra al terminar.
Eso pasa muchas veces por segundo cuando se listan tablas o se cambia
de pantalla, y como la interfaz GTK corre en un solo hilo, la ventana
se congela mientras espera cada conexion nueva.

La solucion: reutilizar UNA sola conexion abierta para todas las
operaciones remotas, en vez de abrir/cerrar una por cada llamada.
Esto NO cambia ninguna consulta SQL ni ninguna funcion de negocio: solo
cambia como se maneja la conexion, dentro de api_conectar()/
api_desconectar() (que ya usan las 19 funciones migradas hasta ahora).

Detalle importante: los servidores SQL a veces cierran conexiones
inactivas despues de varios minutos. Para que PawOS no se quede
"pegado" si eso pasa, se agrega una revision: si la conexion guardada
lleva mas de 4 minutos sin usarse, se descarta y se abre una nueva
automaticamente (transparente para el usuario).

IMPORTANTE - antes de correr esto:
  Debes haber corrido ya parche-mascotas-sql-server.py (este script
  solo modifica api_conectar/api_desconectar, que insertó ese parche).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-optimizar-conexion-persistente.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")

ANCLA = """static int api_conectar(SQLHENV *out_henv, SQLHDBC *out_hdbc) {
    char pass[128];
    if (api_leer_password_remota(pass, sizeof(pass)) != 0) return -1;

    char connstr[512];
    snprintf(connstr, sizeof(connstr),
        "DRIVER={FreeTDS};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;TDS_Version=7.4;",
        API_SQL_SERVIDOR, API_SQL_PUERTO, API_SQL_BASE, API_SQL_USUARIO, pass);

    SQLHENV henv;
    if (SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &henv) != SQL_SUCCESS) return -1;
    SQLSetEnvAttr(henv, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);

    SQLHDBC hdbc;
    if (SQLAllocHandle(SQL_HANDLE_DBC, henv, &hdbc) != SQL_SUCCESS) {
        SQLFreeHandle(SQL_HANDLE_ENV, henv);
        return -1;
    }

    SQLCHAR outstr[512];
    SQLSMALLINT outstrlen;
    SQLRETURN ret = SQLDriverConnect(hdbc, NULL, (SQLCHAR *)connstr, SQL_NTS,
                                      outstr, sizeof(outstr), &outstrlen,
                                      SQL_DRIVER_NOPROMPT);
    if (!SQL_SUCCEEDED(ret)) {
        SQLFreeHandle(SQL_HANDLE_DBC, hdbc);
        SQLFreeHandle(SQL_HANDLE_ENV, henv);
        return -1;
    }

    *out_henv = henv;
    *out_hdbc = hdbc;
    return 0;
}

static void api_desconectar(SQLHENV henv, SQLHDBC hdbc) {
    SQLDisconnect(hdbc);
    SQLFreeHandle(SQL_HANDLE_DBC, hdbc);
    SQLFreeHandle(SQL_HANDLE_ENV, henv);
}"""

NUEVO = """static SQLHENV g_henv_remoto = NULL;
static SQLHDBC  g_hdbc_remoto = NULL;
static time_t   g_ultimo_uso_remoto = 0;
static int      g_atexit_registrado_remoto = 0;
#define API_SQL_MAX_IDLE_SEG 240 /* si pasan mas de 4 min sin usarla, se reconecta por si el servidor la cerro */

static void api_cerrar_conexion_remota(void) {
    if (g_hdbc_remoto != NULL) {
        SQLDisconnect(g_hdbc_remoto);
        SQLFreeHandle(SQL_HANDLE_DBC, g_hdbc_remoto);
        g_hdbc_remoto = NULL;
    }
    if (g_henv_remoto != NULL) {
        SQLFreeHandle(SQL_HANDLE_ENV, g_henv_remoto);
        g_henv_remoto = NULL;
    }
}

static int api_conectar(SQLHENV *out_henv, SQLHDBC *out_hdbc) {
    /* Reutiliza una conexion ya abierta en vez de reconectar por
     * internet en cada operacion (eso era lo que causaba la lentitud). */
    time_t ahora = time(NULL);
    if (g_hdbc_remoto != NULL && (ahora - g_ultimo_uso_remoto) > API_SQL_MAX_IDLE_SEG) {
        api_cerrar_conexion_remota();
    }
    if (g_hdbc_remoto != NULL) {
        g_ultimo_uso_remoto = ahora;
        *out_henv = g_henv_remoto;
        *out_hdbc = g_hdbc_remoto;
        return 0;
    }

    char pass[128];
    if (api_leer_password_remota(pass, sizeof(pass)) != 0) return -1;

    char connstr[512];
    snprintf(connstr, sizeof(connstr),
        "DRIVER={FreeTDS};SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;TDS_Version=7.4;",
        API_SQL_SERVIDOR, API_SQL_PUERTO, API_SQL_BASE, API_SQL_USUARIO, pass);

    SQLHENV henv;
    if (SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &henv) != SQL_SUCCESS) return -1;
    SQLSetEnvAttr(henv, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);

    SQLHDBC hdbc;
    if (SQLAllocHandle(SQL_HANDLE_DBC, henv, &hdbc) != SQL_SUCCESS) {
        SQLFreeHandle(SQL_HANDLE_ENV, henv);
        return -1;
    }

    SQLCHAR outstr[512];
    SQLSMALLINT outstrlen;
    SQLRETURN ret = SQLDriverConnect(hdbc, NULL, (SQLCHAR *)connstr, SQL_NTS,
                                      outstr, sizeof(outstr), &outstrlen,
                                      SQL_DRIVER_NOPROMPT);
    if (!SQL_SUCCEEDED(ret)) {
        SQLFreeHandle(SQL_HANDLE_DBC, hdbc);
        SQLFreeHandle(SQL_HANDLE_ENV, henv);
        return -1;
    }

    g_henv_remoto = henv;
    g_hdbc_remoto = hdbc;
    g_ultimo_uso_remoto = ahora;
    if (!g_atexit_registrado_remoto) {
        atexit(api_cerrar_conexion_remota);
        g_atexit_registrado_remoto = 1;
    }
    *out_henv = henv;
    *out_hdbc = hdbc;
    return 0;
}

static void api_desconectar(SQLHENV henv, SQLHDBC hdbc) {
    /* Ya no se cierra aqui: se mantiene la conexion abierta y se
     * reutiliza en la siguiente operacion (ver api_conectar arriba).
     * Se cierra una sola vez al salir del programa. */
    (void)henv; (void)hdbc;
}"""


def main():
    if not DB_C.exists():
        print(f"ERROR: no se encontro {DB_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = DB_C.read_text(encoding="utf-8")

    apariciones = contenido.count(ANCLA)
    if apariciones == 0:
        print("ERROR: no se encontro el ancla de api_conectar/api_desconectar en src/db/db.c.")
        print("       (puede que ya este parchado, o el codigo cambio)")
        sys.exit(1)
    if apariciones > 1:
        print("ERROR: el ancla aparece mas de una vez, no es seguro parchar automaticamente.")
        sys.exit(1)

    backup = DB_C.with_suffix(".c.bak_conexion_persistente")
    shutil.copy(DB_C, backup)

    contenido = contenido.replace(ANCLA, NUEVO, 1)
    DB_C.write_text(contenido, encoding="utf-8")

    print(f"  {DB_C}: api_conectar/api_desconectar ahora reutilizan una conexion persistente.")
    print(f"  Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  1. make gui")
    print("  2. Usa PawOS normal (mascotas, vacunas, adopciones, donantes, alertas)")
    print("     y confirma que ya no se siente trabado al listar/cambiar de pantalla.")


if __name__ == "__main__":
    main()
