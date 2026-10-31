#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-mascotas-sql-server.py

Convierte el modulo de "Gestion de Mascotas" para que use la base de
datos SQL Server compartida (SmarterASP) en vez de la SQLite local,
SIN tocar el resto de modulos (vacunas, adopciones, donantes, etc.
siguen usando SQLite normal) y SIN cambiar ni una linea de
main_gtk.c / pantallas.c: las 6 funciones mascota_* en src/db/db.c
mantienen exactamente el mismo nombre y firma, solo cambia lo que
hacen por dentro.

Requiere en la VM (antes de compilar):
    sudo apt install -y freetds-bin freetds-dev tdsodbc unixodbc unixodbc-dev

Requiere que exista el archivo ~/.pawos_db_remota con la contrasena
de la base de datos remota (una sola linea, sin saltos extra):
    echo -n 'TU_CONTRASENA_REAL' > ~/.pawos_db_remota
    chmod 600 ~/.pawos_db_remota
Esto es a proposito para que la contrasena NUNCA quede escrita en el
codigo fuente que se sube a GitHub (el repo es publico).

Uso: parado en la raiz del repo:
    python3 parche-mascotas-sql-server.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")
MAKEFILE = Path("Makefile")


def aplicar(ruta: Path, reemplazos, backup_sufijo: str):
    if not ruta.exists():
        print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
        sys.exit(1)
    original = ruta.read_text(encoding="utf-8")
    contenido = original
    for i, (ancla, nuevo) in enumerate(reemplazos, 1):
        if ancla not in contenido:
            print(f"ERROR: no se encontro el fragmento #{i} esperado en {ruta}.")
            print("       (puede que el archivo ya este parchado, o que haya cambiado)")
            print("----- fragmento buscado -----")
            print(ancla[:300])
            print("------------------------------")
            sys.exit(1)
        contenido = contenido.replace(ancla, nuevo, 1)
    backup = ruta.with_suffix(ruta.suffix + backup_sufijo)
    shutil.copy(ruta, backup)
    ruta.write_text(contenido, encoding="utf-8")
    print(f"  {ruta}: {len(reemplazos)} cambio(s) aplicado(s). Respaldo en {backup}")


# ---------------------------------------------------------------------------
# 1) src/db/db.c
# ---------------------------------------------------------------------------

ANCLA_INCLUDES = '#include "db.h"'

NUEVO_INCLUDES = '''#include "db.h"

/* ====================================================================
 * Conexion remota a SQL Server (SmarterASP) SOLO para el modulo de
 * Gestion de Mascotas. Se agrego para compartir esta tabla entre
 * todas las instalaciones del equipo (antes cada quien tenia su
 * propio pawos.db local y por eso cada quien veia datos distintos).
 * El resto de tablas (vacunas, adopciones, donantes, alertas, etc.)
 * NO se toco, siguen usando SQLite local normal.
 *
 * La contrasena de la base de datos NUNCA se escribe aqui: se lee en
 * tiempo de ejecucion desde ~/.pawos_db_remota (un archivo local que
 * cada quien crea a mano, fuera del repositorio de git), porque este
 * repositorio es publico en GitHub.
 * ==================================================================== */
#include <sql.h>
#include <sqlext.h>

#define API_SQL_SERVIDOR  "sql5111.site4now.net"
#define API_SQL_PUERTO    "1433"
#define API_SQL_BASE      "db_ace27e_pawos"
#define API_SQL_USUARIO   "db_ace27e_pawos_admin"

static int api_leer_password_remota(char *out, size_t out_len) {
    const char *home = getenv("HOME");
    char ruta[256];
    snprintf(ruta, sizeof(ruta), "%s/.pawos_db_remota", home ? home : ".");
    FILE *f = fopen(ruta, "r");
    if (!f) return -1;
    if (!fgets(out, (int)out_len, f)) { fclose(f); return -1; }
    out[strcspn(out, "\\r\\n")] = '\\0';
    fclose(f);
    return 0;
}

static int api_conectar(SQLHENV *out_henv, SQLHDBC *out_hdbc) {
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
}

static void api_leer_fila_mascota(SQLHSTMT hstmt, Mascota *m) {
    SQLLEN ind;
    memset(m, 0, sizeof(*m));
    SQLGetData(hstmt, 1, SQL_C_LONG, &m->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_CHAR, m->nombre, sizeof(m->nombre), &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, m->especie, sizeof(m->especie), &ind);
    SQLGetData(hstmt, 4, SQL_C_CHAR, m->raza, sizeof(m->raza), &ind);
    if (ind == SQL_NULL_DATA) m->raza[0] = '\\0';
    SQLGetData(hstmt, 5, SQL_C_LONG, &m->edad, 0, &ind);
    SQLGetData(hstmt, 6, SQL_C_CHAR, m->estado, sizeof(m->estado), &ind);
    SQLGetData(hstmt, 7, SQL_C_CHAR, m->fecha_ingreso, sizeof(m->fecha_ingreso), &ind);
}
/* ==== Fin de utilidades de conexion remota ==== */
'''

ANCLA_LISTAR_DISPONIBLES = '''int mascota_listar_disponibles(Mascota **out, int *n) {
    const char *sql =
        "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas "
        "WHERE estado='disponible' ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        Mascota *m = &arr[cnt++];
        memset(m, 0, sizeof(*m));
        m->id = sqlite3_column_int(st, 0);
        snprintf(m->nombre, sizeof(m->nombre), "%s", (const char *)sqlite3_column_text(st, 1));
        snprintf(m->especie, sizeof(m->especie), "%s", (const char *)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(m->raza, sizeof(m->raza), "%s", raza ? (const char *)raza : "");
        m->edad = sqlite3_column_int(st, 4);
        snprintf(m->estado, sizeof(m->estado), "%s", (const char *)sqlite3_column_text(st, 5));
        snprintf(m->fecha_ingreso, sizeof(m->fecha_ingreso), "%s", (const char *)sqlite3_column_text(st, 6));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}'''

NUEVO_LISTAR_DISPONIBLES = '''int mascota_listar_disponibles(Mascota **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas "
        "WHERE estado='disponible' ORDER BY id;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        api_leer_fila_mascota(hstmt, &arr[cnt++]);
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}'''

ANCLA_LISTAR = '''int mascota_listar(Mascota **out, int *n) {
    const char *sql = "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        Mascota *m = &arr[cnt++];
        memset(m, 0, sizeof(*m));
        m->id = sqlite3_column_int(st, 0);
        snprintf(m->nombre, sizeof(m->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        snprintf(m->especie, sizeof(m->especie), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(m->raza, sizeof(m->raza), "%s", raza ? (const char*)raza : "");
        m->edad = sqlite3_column_int(st, 4);
        snprintf(m->estado, sizeof(m->estado), "%s", (const char*)sqlite3_column_text(st, 5));
        snprintf(m->fecha_ingreso, sizeof(m->fecha_ingreso), "%s", (const char*)sqlite3_column_text(st, 6));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}'''

NUEVO_LISTAR = '''int mascota_listar(Mascota **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas ORDER BY id;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        api_leer_fila_mascota(hstmt, &arr[cnt++]);
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}'''

ANCLA_AGREGAR = '''int mascota_agregar(const Mascota *m) {
    const char *sql =
        "INSERT INTO mascotas (nombre, especie, raza, edad, estado, fecha_ingreso) "
        "VALUES (?,?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, m->nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, m->especie, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, m->raza, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 4, m->edad);
    sqlite3_bind_text(st, 5, m->estado[0] ? m->estado : "disponible", -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 6, m->fecha_ingreso, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_AGREGAR = '''int mascota_agregar(const Mascota *m) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)
        "INSERT INTO mascotas (nombre,especie,raza,edad,estado,fecha_ingreso) "
        "VALUES (?,?,?,?,?,?);", SQL_NTS);

    char nombre_buf[64], especie_buf[32], raza_buf[32], estado_buf[16], fecha_buf[16];
    snprintf(nombre_buf, sizeof(nombre_buf), "%s", m->nombre);
    snprintf(especie_buf, sizeof(especie_buf), "%s", m->especie);
    snprintf(raza_buf, sizeof(raza_buf), "%s", m->raza);
    snprintf(estado_buf, sizeof(estado_buf), "%s", m->estado[0] ? m->estado : "disponible");
    snprintf(fecha_buf, sizeof(fecha_buf), "%s", m->fecha_ingreso);
    SQLINTEGER edad_val = m->edad;

    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(nombre_buf) - 1, 0, nombre_buf, 0, NULL);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(especie_buf) - 1, 0, especie_buf, 0, NULL);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(raza_buf) - 1, 0, raza_buf, 0, NULL);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &edad_val, 0, NULL);
    SQLBindParameter(hstmt, 5, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(estado_buf) - 1, 0, estado_buf, 0, NULL);
    SQLBindParameter(hstmt, 6, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(fecha_buf) - 1, 0, fecha_buf, 0, NULL);

    SQLRETURN ret = SQLExecute(hstmt);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return SQL_SUCCEEDED(ret) ? 0 : -1;
}'''

ANCLA_ACTUALIZAR = '''int mascota_actualizar_estado(int id, const char *nuevo_estado) {
    const char *sql = "UPDATE mascotas SET estado=? WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, nuevo_estado, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 2, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_ACTUALIZAR = '''int mascota_actualizar_estado(int id, const char *nuevo_estado) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)"UPDATE mascotas SET estado=? WHERE id=?;", SQL_NTS);

    char estado_buf[16];
    snprintf(estado_buf, sizeof(estado_buf), "%s", nuevo_estado);
    SQLINTEGER id_val = id;

    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(estado_buf) - 1, 0, estado_buf, 0, NULL);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);

    SQLRETURN ret = SQLExecute(hstmt);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return SQL_SUCCEEDED(ret) ? 0 : -1;
}'''

ANCLA_ELIMINAR = '''int mascota_eliminar(int id) {
    const char *sql = "DELETE FROM mascotas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_ELIMINAR = '''int mascota_eliminar(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)"DELETE FROM mascotas WHERE id=?;", SQL_NTS);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);

    SQLRETURN ret = SQLExecute(hstmt);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return SQL_SUCCEEDED(ret) ? 0 : -1;
}'''

ANCLA_BUSCAR = '''int mascota_buscar_por_id(int id, Mascota *out) {
    const char *sql = "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int found = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        memset(out, 0, sizeof(*out));
        out->id = sqlite3_column_int(st, 0);
        snprintf(out->nombre, sizeof(out->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        snprintf(out->especie, sizeof(out->especie), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(out->raza, sizeof(out->raza), "%s", raza ? (const char*)raza : "");
        out->edad = sqlite3_column_int(st, 4);
        snprintf(out->estado, sizeof(out->estado), "%s", (const char*)sqlite3_column_text(st, 5));
        snprintf(out->fecha_ingreso, sizeof(out->fecha_ingreso), "%s", (const char*)sqlite3_column_text(st, 6));
        found = 0;
    }
    sqlite3_finalize(st);
    return found;
}'''

NUEVO_BUSCAR = '''int mascota_buscar_por_id(int id, Mascota *out) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)
        "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas WHERE id=?;", SQL_NTS);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);

    int found = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        api_leer_fila_mascota(hstmt, out);
        found = 0;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return found;
}'''

REEMPLAZOS_DB_C = [
    (ANCLA_INCLUDES, NUEVO_INCLUDES),
    (ANCLA_LISTAR_DISPONIBLES, NUEVO_LISTAR_DISPONIBLES),
    (ANCLA_LISTAR, NUEVO_LISTAR),
    (ANCLA_AGREGAR, NUEVO_AGREGAR),
    (ANCLA_ACTUALIZAR, NUEVO_ACTUALIZAR),
    (ANCLA_ELIMINAR, NUEVO_ELIMINAR),
    (ANCLA_BUSCAR, NUEVO_BUSCAR),
]


def main():
    if not Path("Makefile").exists():
        print("ERROR: corre este script desde la raiz del repo (donde esta el Makefile).")
        sys.exit(1)

    print("==> Parchando src/db/db.c (modulo de Gestion de Mascotas -> SQL Server)...")
    aplicar(DB_C, REEMPLAZOS_DB_C, ".bak_sqlserver")

    print("==> Agregando -lodbc a las reglas de compilacion en Makefile...")
    makefile_txt = MAKEFILE.read_text(encoding="utf-8")
    objetivo = "-lsqlite3 -lm -lcrypt"
    if objetivo not in makefile_txt:
        print("ERROR: no se encontro '-lsqlite3 -lm -lcrypt' en el Makefile.")
        sys.exit(1)
    n = makefile_txt.count(objetivo)
    shutil.copy(MAKEFILE, MAKEFILE.with_suffix(".bak_sqlserver"))
    makefile_txt = makefile_txt.replace(objetivo, objetivo + " -lodbc")
    MAKEFILE.write_text(makefile_txt, encoding="utf-8")
    print(f"  Makefile: se agrego -lodbc en {n} lugar(es). Respaldo en Makefile.bak_sqlserver")

    print("")
    print("==========================================================")
    print(" Listo. Antes de compilar:")
    print("   1) Asegurate de tener instalado:")
    print("        sudo apt install -y freetds-bin freetds-dev tdsodbc unixodbc unixodbc-dev")
    print("   2) Asegurate de tener el archivo con la contrasena:")
    print("        cat ~/.pawos_db_remota   (debe mostrar tu contrasena, una sola linea)")
    print(" Luego compila normalmente:")
    print("   make gui")
    print("   ./pawos-refugio-gui")
    print("==========================================================")


if __name__ == "__main__":
    main()
