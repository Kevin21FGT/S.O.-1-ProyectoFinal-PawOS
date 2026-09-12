#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-vacunas-sql-server.py

Convierte las 8 funciones vacuna_* en src/db/db.c para que usen la
misma base de datos SQL Server compartida (SmarterASP) que ya usa
Gestion de Mascotas, via ODBC/FreeTDS (reutiliza api_conectar() /
api_desconectar() que ya estan en el archivo desde el parche de
mascotas).

NO cambia nombres ni firmas de funciones: main_gtk.c y pantallas.c
quedan intactos.

IMPORTANTE - antes de correr esto:
  1. Debes haber corrido ya parche-mascotas-sql-server.py (este script
     depende de que api_conectar/api_desconectar ya existan en db.c).
  2. Debes crear la tabla "vacunas" en la base de datos SQL Server
     (db_ace27e_pawos) usando el SQL Studio Portal de SmarterASP:

     CREATE TABLE vacunas (
         id INT IDENTITY(1,1) PRIMARY KEY,
         mascota_id INT NOT NULL,
         nombre_vacuna VARCHAR(64) NOT NULL,
         fecha_aplicacion VARCHAR(16) NOT NULL,
         fecha_proxima VARCHAR(16) NULL,
         observaciones VARCHAR(128) NULL,
         cliente_id INT NULL,
         recordatorio_enviado INT NOT NULL DEFAULT 0
     );

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-vacunas-sql-server.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")

# ---------------------------------------------------------------------------
# 1) Insertar helper api_leer_fila_vacuna_base justo despues del helper
#    de mascotas que ya inserto parche-mascotas-sql-server.py.
# ---------------------------------------------------------------------------
ANCLA_HELPER = """static void api_leer_fila_mascota(SQLHSTMT hstmt, Mascota *m) {
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
}"""

NUEVO_HELPER = ANCLA_HELPER + """

/* Helper equivalente para Vacuna. Lee las primeras 6 columnas comunes
 * a todas las consultas (id,mascota_id,nombre_vacuna,fecha_aplicacion,
 * fecha_proxima,observaciones). cliente_id se lee aparte en cada
 * funcion porque no todas las consultas lo incluyen (igual que en el
 * codigo original con SQLite). */
static void api_leer_fila_vacuna_base(SQLHSTMT hstmt, Vacuna *v) {
    SQLLEN ind;
    memset(v, 0, sizeof(*v));
    SQLGetData(hstmt, 1, SQL_C_LONG, &v->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_LONG, &v->mascota_id, 0, &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, v->nombre_vacuna, sizeof(v->nombre_vacuna), &ind);
    SQLGetData(hstmt, 4, SQL_C_CHAR, v->fecha_aplicacion, sizeof(v->fecha_aplicacion), &ind);
    SQLGetData(hstmt, 5, SQL_C_CHAR, v->fecha_proxima, sizeof(v->fecha_proxima), &ind);
    if (ind == SQL_NULL_DATA) v->fecha_proxima[0] = '\\0';
    SQLGetData(hstmt, 6, SQL_C_CHAR, v->observaciones, sizeof(v->observaciones), &ind);
    if (ind == SQL_NULL_DATA) v->observaciones[0] = '\\0';
}"""

# ---------------------------------------------------------------------------
# 2) Las 8 funciones vacuna_*
# ---------------------------------------------------------------------------
ANCLA_AGREGAR = """int vacuna_agregar(const Vacuna *v) {
    const char *sql =
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima, observaciones, cliente_id) "
        "VALUES (?,?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, v->mascota_id);
    sqlite3_bind_text(st, 2, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 5, v->observaciones, -1, SQLITE_STATIC);
    if (v->cliente_id > 0) {
        sqlite3_bind_int(st, 6, v->cliente_id);
    } else {
        sqlite3_bind_null(st, 6);
    }
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_AGREGAR = """int vacuna_agregar(const Vacuna *v) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima, observaciones, cliente_id) "
        "VALUES (?,?,?,?,?,?);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER mascota_id = v->mascota_id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &mascota_id, 0, NULL);
    SQLLEN len_nombre = SQL_NTS, len_fapl = SQL_NTS, len_fprox = SQL_NTS, len_obs = SQL_NTS;
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->nombre_vacuna), 0, (SQLPOINTER)v->nombre_vacuna, 0, &len_nombre);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->fecha_aplicacion), 0, (SQLPOINTER)v->fecha_aplicacion, 0, &len_fapl);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->fecha_proxima), 0, (SQLPOINTER)v->fecha_proxima, 0, &len_fprox);
    SQLBindParameter(hstmt, 5, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->observaciones), 0, (SQLPOINTER)v->observaciones, 0, &len_obs);
    SQLINTEGER cliente_id = v->cliente_id;
    SQLLEN ind_cliente = (v->cliente_id > 0) ? 0 : SQL_NULL_DATA;
    SQLBindParameter(hstmt, 6, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &cliente_id, 0, &ind_cliente);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

ANCLA_BUSCAR = """int vacuna_buscar_por_id(int id, Vacuna *out) {
    const char *sql = "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int found = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        memset(out, 0, sizeof(*out));
        out->id = sqlite3_column_int(st, 0);
        out->mascota_id = sqlite3_column_int(st, 1);
        snprintf(out->nombre_vacuna, sizeof(out->nombre_vacuna), "%s", (const char*)sqlite3_column_text(st, 2));
        snprintf(out->fecha_aplicacion, sizeof(out->fecha_aplicacion), "%s", (const char*)sqlite3_column_text(st, 3));
        const unsigned char *fp = sqlite3_column_text(st, 4);
        snprintf(out->fecha_proxima, sizeof(out->fecha_proxima), "%s", fp ? (const char*)fp : "");
        const unsigned char *obs = sqlite3_column_text(st, 5);
        snprintf(out->observaciones, sizeof(out->observaciones), "%s", obs ? (const char*)obs : "");
        found = 0;
    }
    sqlite3_finalize(st);
    return found;
}"""

NUEVO_BUSCAR = """int vacuna_buscar_por_id(int id, Vacuna *out) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones FROM vacunas WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_param = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_param, 0, NULL);
    int found = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        api_leer_fila_vacuna_base(hstmt, out);
        found = 0;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return found;
}"""

ANCLA_ACTUALIZAR = """int vacuna_actualizar(const Vacuna *v) {
    const char *sql = "UPDATE vacunas SET nombre_vacuna=?, fecha_aplicacion=?, fecha_proxima=?, observaciones=? WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->observaciones, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 5, v->id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_ACTUALIZAR = """int vacuna_actualizar(const Vacuna *v) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE vacunas SET nombre_vacuna=?, fecha_aplicacion=?, fecha_proxima=?, observaciones=? WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len1 = SQL_NTS, len2 = SQL_NTS, len3 = SQL_NTS, len4 = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->nombre_vacuna), 0, (SQLPOINTER)v->nombre_vacuna, 0, &len1);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->fecha_aplicacion), 0, (SQLPOINTER)v->fecha_aplicacion, 0, &len2);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->fecha_proxima), 0, (SQLPOINTER)v->fecha_proxima, 0, &len3);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(v->observaciones), 0, (SQLPOINTER)v->observaciones, 0, &len4);
    SQLINTEGER id_param = v->id;
    SQLBindParameter(hstmt, 5, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_param, 0, NULL);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

ANCLA_ELIMINAR = """int vacuna_eliminar(int id) {
    const char *sql = "DELETE FROM vacunas WHERE id=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_ELIMINAR = """int vacuna_eliminar(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "DELETE FROM vacunas WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_param = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_param, 0, NULL);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

ANCLA_LISTAR = """int vacuna_listar(Vacuna **out, int *n) {
    return vacuna_query(
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas ORDER BY fecha_proxima;",
        out, n);
}"""

NUEVO_LISTAR = """int vacuna_listar(Vacuna **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas ORDER BY fecha_proxima;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Vacuna *arr = malloc(sizeof(Vacuna) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) {
            cap *= 2;
            arr = realloc(arr, sizeof(Vacuna) * cap);
        }
        api_leer_fila_vacuna_base(hstmt, &arr[cnt]);
        SQLLEN ind;
        SQLGetData(hstmt, 7, SQL_C_LONG, &arr[cnt].cliente_id, 0, &ind);
        if (ind == SQL_NULL_DATA) arr[cnt].cliente_id = 0;
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

ANCLA_PENDIENTES = """int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);
    return vacuna_query(sql, out, n);
}"""

NUEVO_PENDIENTES = """int vacuna_pendientes(Vacuna **out, int *n) {
    char sql[256];
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char hoy[16];
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);
    snprintf(sql, sizeof(sql),
        "SELECT id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id FROM vacunas "
        "WHERE fecha_proxima IS NOT NULL AND fecha_proxima <= '%s' ORDER BY fecha_proxima;", hoy);

    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Vacuna *arr = malloc(sizeof(Vacuna) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) {
            cap *= 2;
            arr = realloc(arr, sizeof(Vacuna) * cap);
        }
        api_leer_fila_vacuna_base(hstmt, &arr[cnt]);
        SQLLEN ind;
        SQLGetData(hstmt, 7, SQL_C_LONG, &arr[cnt].cliente_id, 0, &ind);
        if (ind == SQL_NULL_DATA) arr[cnt].cliente_id = 0;
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

ANCLA_RECORDATORIO = """int vacuna_recordatorio_enviado(int id) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "SELECT recordatorio_enviado FROM vacunas WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return 0;
    sqlite3_bind_int(st, 1, id);
    int enviado = 0;
    if (sqlite3_step(st) == SQLITE_ROW) enviado = sqlite3_column_int(st, 0);
    sqlite3_finalize(st);
    return enviado;
}"""

NUEVO_RECORDATORIO = """int vacuna_recordatorio_enviado(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return 0;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return 0;
    }
    const char *sql = "SELECT recordatorio_enviado FROM vacunas WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_param = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_param, 0, NULL);
    int enviado = 0;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        SQLLEN ind;
        SQLGetData(hstmt, 1, SQL_C_LONG, &enviado, 0, &ind);
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return enviado;
}"""

ANCLA_MARCAR = """int vacuna_marcar_recordatorio_enviado(int id) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "UPDATE vacunas SET recordatorio_enviado=1 WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_MARCAR = """int vacuna_marcar_recordatorio_enviado(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE vacunas SET recordatorio_enviado=1 WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_param = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_param, 0, NULL);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

REEMPLAZOS = [
    ("helper api_leer_fila_vacuna_base", ANCLA_HELPER, NUEVO_HELPER),
    ("vacuna_agregar", ANCLA_AGREGAR, NUEVO_AGREGAR),
    ("vacuna_buscar_por_id", ANCLA_BUSCAR, NUEVO_BUSCAR),
    ("vacuna_actualizar", ANCLA_ACTUALIZAR, NUEVO_ACTUALIZAR),
    ("vacuna_eliminar", ANCLA_ELIMINAR, NUEVO_ELIMINAR),
    ("vacuna_listar", ANCLA_LISTAR, NUEVO_LISTAR),
    ("vacuna_pendientes", ANCLA_PENDIENTES, NUEVO_PENDIENTES),
    ("vacuna_recordatorio_enviado", ANCLA_RECORDATORIO, NUEVO_RECORDATORIO),
    ("vacuna_marcar_recordatorio_enviado", ANCLA_MARCAR, NUEVO_MARCAR),
]


def main():
    if not DB_C.exists():
        print(f"ERROR: no se encontro {DB_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = DB_C.read_text(encoding="utf-8")

    faltantes = []
    for nombre, ancla, _ in REEMPLAZOS:
        if contenido.count(ancla) == 0:
            faltantes.append(nombre)
        elif contenido.count(ancla) > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar automaticamente.")
            sys.exit(1)

    if faltantes:
        print("ERROR: no se encontraron estas anclas en src/db/db.c (puede que ya este parchado, o el codigo cambio):")
        for nombre in faltantes:
            print(f"  - {nombre}")
        sys.exit(1)

    backup = DB_C.with_suffix(".c.bak_vacunas_sqlserver")
    shutil.copy(DB_C, backup)

    for nombre, ancla, nuevo in REEMPLAZOS:
        contenido = contenido.replace(ancla, nuevo, 1)

    DB_C.write_text(contenido, encoding="utf-8")

    print(f"  {DB_C}: 8 funciones vacuna_* + helper migradas a SQL Server via ODBC.")
    print(f"  Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO (si no lo has hecho ya):")
    print("  1. Crea la tabla 'vacunas' en SQL Studio Portal (db_ace27e_pawos):")
    print()
    print("     CREATE TABLE vacunas (")
    print("         id INT IDENTITY(1,1) PRIMARY KEY,")
    print("         mascota_id INT NOT NULL,")
    print("         nombre_vacuna VARCHAR(64) NOT NULL,")
    print("         fecha_aplicacion VARCHAR(16) NOT NULL,")
    print("         fecha_proxima VARCHAR(16) NULL,")
    print("         observaciones VARCHAR(128) NULL,")
    print("         cliente_id INT NULL,")
    print("         recordatorio_enviado INT NOT NULL DEFAULT 0")
    print("     );")
    print()
    print("  2. make gui")
    print("  3. Prueba desde PawOS: registrar una vacuna, listarla, marcarla")
    print("     pendiente/eliminarla, y confirma que aparece en SQL Studio Portal.")


if __name__ == "__main__":
    main()
