#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-adopciones-donantes-alertas-sql-server.py

Migra los modulos de Adopciones, Donantes y Alertas de Sensores en
src/db/db.c a la misma base de datos SQL Server compartida
(SmarterASP) via ODBC/FreeTDS, reutilizando api_conectar() /
api_desconectar() ya presentes en el archivo (parche de mascotas).

NO cambia nombres ni firmas de funciones.

IMPORTANTE - detalle de "adopcion_registrar":
El codigo original hacia esto en UNA transaccion de SQLite:
  1) insertar en "adopciones"
  2) marcar la mascota como "adoptado" (mascota_actualizar_estado)
Para no perder esa atomicidad (que ambas cosas pasen o ninguna), la
version nueva abre UNA sola conexion ODBC, desactiva autocommit, hace
el INSERT y el UPDATE de mascotas en esa misma conexion/transaccion,
y al final hace COMMIT (o ROLLBACK si algo falla). No llama a
mascota_actualizar_estado() para este caso especifico, precisamente
para que ambas escrituras queden dentro de la misma transaccion.

IMPORTANTE - antes de correr esto:
  1. Debes haber corrido ya parche-mascotas-sql-server.py y
     parche-vacunas-sql-server.py (este script depende de
     api_conectar/api_desconectar y de que exista
     api_leer_fila_vacuna_base en el archivo).
  2. Crea estas 3 tablas en SQL Studio Portal (db_ace27e_pawos):

     CREATE TABLE adopciones (
         id INT IDENTITY(1,1) PRIMARY KEY,
         mascota_id INT NOT NULL,
         adoptante_nombre VARCHAR(64) NOT NULL,
         adoptante_contacto VARCHAR(64) NULL,
         fecha_adopcion VARCHAR(16) NOT NULL
     );

     CREATE TABLE donantes (
         id INT IDENTITY(1,1) PRIMARY KEY,
         nombre VARCHAR(64) NOT NULL,
         contacto VARCHAR(64) NULL,
         monto FLOAT NOT NULL,
         fecha VARCHAR(16) NOT NULL
     );

     CREATE TABLE alertas_sensores (
         id INT IDENTITY(1,1) PRIMARY KEY,
         animal_id VARCHAR(32) NOT NULL,
         tipo VARCHAR(32) NOT NULL,
         detalle VARCHAR(128) NULL,
         valor FLOAT NOT NULL,
         fecha_hora VARCHAR(24) NOT NULL,
         atendida INT NOT NULL DEFAULT 0
     );

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-adopciones-donantes-alertas-sql-server.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")

# ---------------------------------------------------------------------------
# 1) Insertar 3 helpers nuevos justo despues de api_leer_fila_vacuna_base
#    (insertado por el parche de vacunas).
# ---------------------------------------------------------------------------
ANCLA_HELPERS = """static void api_leer_fila_vacuna_base(SQLHSTMT hstmt, Vacuna *v) {
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

NUEVO_HELPERS = ANCLA_HELPERS + """

static void api_leer_fila_adopcion(SQLHSTMT hstmt, Adopcion *a) {
    SQLLEN ind;
    memset(a, 0, sizeof(*a));
    SQLGetData(hstmt, 1, SQL_C_LONG, &a->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_LONG, &a->mascota_id, 0, &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, a->adoptante_nombre, sizeof(a->adoptante_nombre), &ind);
    SQLGetData(hstmt, 4, SQL_C_CHAR, a->adoptante_contacto, sizeof(a->adoptante_contacto), &ind);
    if (ind == SQL_NULL_DATA) a->adoptante_contacto[0] = '\\0';
    SQLGetData(hstmt, 5, SQL_C_CHAR, a->fecha_adopcion, sizeof(a->fecha_adopcion), &ind);
}

static void api_leer_fila_donante(SQLHSTMT hstmt, Donante *d) {
    SQLLEN ind;
    memset(d, 0, sizeof(*d));
    SQLGetData(hstmt, 1, SQL_C_LONG, &d->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_CHAR, d->nombre, sizeof(d->nombre), &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, d->contacto, sizeof(d->contacto), &ind);
    if (ind == SQL_NULL_DATA) d->contacto[0] = '\\0';
    SQLGetData(hstmt, 4, SQL_C_DOUBLE, &d->monto, 0, &ind);
    SQLGetData(hstmt, 5, SQL_C_CHAR, d->fecha, sizeof(d->fecha), &ind);
}

static void api_leer_fila_alerta(SQLHSTMT hstmt, Alerta *al) {
    SQLLEN ind;
    memset(al, 0, sizeof(*al));
    SQLGetData(hstmt, 1, SQL_C_LONG, &al->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_CHAR, al->animal_id, sizeof(al->animal_id), &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, al->tipo, sizeof(al->tipo), &ind);
    SQLGetData(hstmt, 4, SQL_C_CHAR, al->detalle, sizeof(al->detalle), &ind);
    if (ind == SQL_NULL_DATA) al->detalle[0] = '\\0';
    SQLGetData(hstmt, 5, SQL_C_DOUBLE, &al->valor, 0, &ind);
    SQLGetData(hstmt, 6, SQL_C_CHAR, al->fecha_hora, sizeof(al->fecha_hora), &ind);
    SQLGetData(hstmt, 7, SQL_C_LONG, &al->atendida, 0, &ind);
}"""

# ---------------------------------------------------------------------------
# 2) Adopciones
# ---------------------------------------------------------------------------
ANCLA_ADOPCION_REGISTRAR = """int adopcion_registrar(const Adopcion *a) {
    /* transaccion: registrar adopcion + marcar mascota como adoptada */
    char *err = NULL;
    sqlite3_exec(g_db, "BEGIN;", NULL, NULL, &err);

    const char *sql =
        "INSERT INTO adopciones (mascota_id, adoptante_nombre, adoptante_contacto, fecha_adopcion) "
        "VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }
    sqlite3_bind_int(st, 1, a->mascota_id);
    sqlite3_bind_text(st, 2, a->adoptante_nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, a->adoptante_contacto, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, a->fecha_adopcion, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    if (rc != SQLITE_DONE) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }

    if (mascota_actualizar_estado(a->mascota_id, "adoptado") != 0) {
        sqlite3_exec(g_db, "ROLLBACK;", NULL, NULL, NULL);
        return -1;
    }

    sqlite3_exec(g_db, "COMMIT;", NULL, NULL, &err);
    return 0;
}"""

NUEVO_ADOPCION_REGISTRAR = """int adopcion_registrar(const Adopcion *a) {
    /* transaccion: registrar adopcion + marcar mascota como adoptada.
     * Se usa UNA sola conexion ODBC con autocommit apagado para que
     * las dos escrituras (adopciones + mascotas) queden en la misma
     * transaccion, igual que hacia el BEGIN/COMMIT/ROLLBACK original. */
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_OFF, 0);

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        SQLEndTran(SQL_HANDLE_DBC, hdbc, SQL_ROLLBACK);
        SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "INSERT INTO adopciones (mascota_id, adoptante_nombre, adoptante_contacto, fecha_adopcion) "
        "VALUES (?,?,?,?);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER mascota_id = a->mascota_id;
    SQLLEN len_nom = SQL_NTS, len_cont = SQL_NTS, len_fecha = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &mascota_id, 0, NULL);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->adoptante_nombre), 0, (SQLPOINTER)a->adoptante_nombre, 0, &len_nom);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->adoptante_contacto), 0, (SQLPOINTER)a->adoptante_contacto, 0, &len_cont);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->fecha_adopcion), 0, (SQLPOINTER)a->fecha_adopcion, 0, &len_fecha);
    SQLRETURN ret = SQLExecute(hstmt);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    if (!SQL_SUCCEEDED(ret)) {
        SQLEndTran(SQL_HANDLE_DBC, hdbc, SQL_ROLLBACK);
        SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
        api_desconectar(henv, hdbc);
        return -1;
    }

    SQLHSTMT hstmt2;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt2) != SQL_SUCCESS) {
        SQLEndTran(SQL_HANDLE_DBC, hdbc, SQL_ROLLBACK);
        SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql2 = "UPDATE mascotas SET estado=? WHERE id=?;";
    SQLPrepare(hstmt2, (SQLCHAR *)sql2, SQL_NTS);
    SQLLEN len_estado = SQL_NTS;
    SQLBindParameter(hstmt2, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 16, 0, (SQLPOINTER)"adoptado", 0, &len_estado);
    SQLINTEGER mascota_id2 = a->mascota_id;
    SQLBindParameter(hstmt2, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &mascota_id2, 0, NULL);
    ret = SQLExecute(hstmt2);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt2);
    if (!SQL_SUCCEEDED(ret)) {
        SQLEndTran(SQL_HANDLE_DBC, hdbc, SQL_ROLLBACK);
        SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
        api_desconectar(henv, hdbc);
        return -1;
    }

    SQLEndTran(SQL_HANDLE_DBC, hdbc, SQL_COMMIT);
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
    api_desconectar(henv, hdbc);
    return 0;
}"""

ANCLA_ADOPCION_LISTAR = """int adopcion_listar(Adopcion **out, int *n) {
    const char *sql =
        "SELECT id,mascota_id,adoptante_nombre,adoptante_contacto,fecha_adopcion FROM adopciones ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Adopcion *arr = malloc(sizeof(Adopcion) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Adopcion) * cap); }
        Adopcion *a = &arr[cnt++];
        memset(a, 0, sizeof(*a));
        a->id = sqlite3_column_int(st, 0);
        a->mascota_id = sqlite3_column_int(st, 1);
        snprintf(a->adoptante_nombre, sizeof(a->adoptante_nombre), "%s", (const char*)sqlite3_column_text(st, 2));
        const unsigned char *c = sqlite3_column_text(st, 3);
        snprintf(a->adoptante_contacto, sizeof(a->adoptante_contacto), "%s", c ? (const char*)c : "");
        snprintf(a->fecha_adopcion, sizeof(a->fecha_adopcion), "%s", (const char*)sqlite3_column_text(st, 4));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}"""

NUEVO_ADOPCION_LISTAR = """int adopcion_listar(Adopcion **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "SELECT id,mascota_id,adoptante_nombre,adoptante_contacto,fecha_adopcion FROM adopciones ORDER BY id;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Adopcion *arr = malloc(sizeof(Adopcion) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) { cap *= 2; arr = realloc(arr, sizeof(Adopcion) * cap); }
        api_leer_fila_adopcion(hstmt, &arr[cnt]);
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

# ---------------------------------------------------------------------------
# 3) Donantes
# ---------------------------------------------------------------------------
ANCLA_DONANTE_AGREGAR = """int donante_agregar(const Donante *d) {
    const char *sql = "INSERT INTO donantes (nombre, contacto, monto, fecha) VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, d->nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, d->contacto, -1, SQLITE_STATIC);
    sqlite3_bind_double(st, 3, d->monto);
    sqlite3_bind_text(st, 4, d->fecha, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_DONANTE_AGREGAR = """int donante_agregar(const Donante *d) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "INSERT INTO donantes (nombre, contacto, monto, fecha) VALUES (?,?,?,?);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len_nom = SQL_NTS, len_cont = SQL_NTS, len_fecha = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(d->nombre), 0, (SQLPOINTER)d->nombre, 0, &len_nom);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(d->contacto), 0, (SQLPOINTER)d->contacto, 0, &len_cont);
    SQLDOUBLE monto = d->monto;
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_DOUBLE, SQL_DOUBLE, 0, 0, &monto, 0, NULL);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(d->fecha), 0, (SQLPOINTER)d->fecha, 0, &len_fecha);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

ANCLA_DONANTE_LISTAR = """int donante_listar(Donante **out, int *n) {
    const char *sql = "SELECT id,nombre,contacto,monto,fecha FROM donantes ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 16, cnt = 0;
    Donante *arr = malloc(sizeof(Donante) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Donante) * cap); }
        Donante *d = &arr[cnt++];
        memset(d, 0, sizeof(*d));
        d->id = sqlite3_column_int(st, 0);
        snprintf(d->nombre, sizeof(d->nombre), "%s", (const char*)sqlite3_column_text(st, 1));
        const unsigned char *c = sqlite3_column_text(st, 2);
        snprintf(d->contacto, sizeof(d->contacto), "%s", c ? (const char*)c : "");
        d->monto = sqlite3_column_double(st, 3);
        snprintf(d->fecha, sizeof(d->fecha), "%s", (const char*)sqlite3_column_text(st, 4));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}"""

NUEVO_DONANTE_LISTAR = """int donante_listar(Donante **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,nombre,contacto,monto,fecha FROM donantes ORDER BY id;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Donante *arr = malloc(sizeof(Donante) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) { cap *= 2; arr = realloc(arr, sizeof(Donante) * cap); }
        api_leer_fila_donante(hstmt, &arr[cnt]);
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

ANCLA_DONANTE_TOTAL = """double donante_total_recaudado(void) {
    const char *sql = "SELECT COALESCE(SUM(monto),0) FROM donantes;";
    sqlite3_stmt *st;
    double total = 0.0;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) == SQLITE_OK) {
        if (sqlite3_step(st) == SQLITE_ROW) total = sqlite3_column_double(st, 0);
    }
    sqlite3_finalize(st);
    return total;
}"""

NUEVO_DONANTE_TOTAL = """double donante_total_recaudado(void) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return 0.0;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return 0.0;
    }
    const char *sql = "SELECT COALESCE(SUM(monto),0) FROM donantes;";
    double total = 0.0;
    if (SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        SQLLEN ind;
        SQLGetData(hstmt, 1, SQL_C_DOUBLE, &total, 0, &ind);
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return total;
}"""

# ---------------------------------------------------------------------------
# 4) Alertas de sensores
# ---------------------------------------------------------------------------
ANCLA_ALERTA_REGISTRAR = """int alerta_registrar(const Alerta *a) {
    const char *sql =
        "INSERT INTO alertas_sensores (animal_id, tipo, detalle, valor, fecha_hora, atendida) "
        "VALUES (?,?,?,?, datetime('now','localtime'), 0);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, a->animal_id, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, a->tipo, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, a->detalle, -1, SQLITE_STATIC);
    sqlite3_bind_double(st, 4, a->valor);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_ALERTA_REGISTRAR = """int alerta_registrar(const Alerta *a) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql =
        "INSERT INTO alertas_sensores (animal_id, tipo, detalle, valor, fecha_hora, atendida) "
        "VALUES (?,?,?,?, CONVERT(varchar(19), GETDATE(), 120), 0);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len_animal = SQL_NTS, len_tipo = SQL_NTS, len_detalle = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->animal_id), 0, (SQLPOINTER)a->animal_id, 0, &len_animal);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->tipo), 0, (SQLPOINTER)a->tipo, 0, &len_tipo);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(a->detalle), 0, (SQLPOINTER)a->detalle, 0, &len_detalle);
    SQLDOUBLE valor = a->valor;
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_DOUBLE, SQL_DOUBLE, 0, 0, &valor, 0, NULL);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}"""

ANCLA_ALERTA_LISTAR = """int alerta_listar(Alerta **out, int *n) {
    return alerta_query(
        "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores ORDER BY id DESC;",
        out, n);
}"""

NUEVO_ALERTA_LISTAR = """int alerta_listar(Alerta **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores ORDER BY id DESC;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Alerta *arr = malloc(sizeof(Alerta) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) { cap *= 2; arr = realloc(arr, sizeof(Alerta) * cap); }
        api_leer_fila_alerta(hstmt, &arr[cnt]);
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

ANCLA_ALERTA_PENDIENTES = """int alerta_pendientes(Alerta **out, int *n) {
    return alerta_query(
        "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores "
        "WHERE atendida = 0 ORDER BY id DESC;",
        out, n);
}"""

NUEVO_ALERTA_PENDIENTES = """int alerta_pendientes(Alerta **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id,animal_id,tipo,detalle,valor,fecha_hora,atendida FROM alertas_sensores "
        "WHERE atendida = 0 ORDER BY id DESC;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 16, cnt = 0;
    Alerta *arr = malloc(sizeof(Alerta) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) { cap *= 2; arr = realloc(arr, sizeof(Alerta) * cap); }
        api_leer_fila_alerta(hstmt, &arr[cnt]);
        cnt++;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}"""

ANCLA_ALERTA_MARCAR = """int alerta_marcar_atendida(int id) {
    const char *sql = "UPDATE alertas_sensores SET atendida = 1 WHERE id = ?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

NUEVO_ALERTA_MARCAR = """int alerta_marcar_atendida(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE alertas_sensores SET atendida = 1 WHERE id = ?;";
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
    ("helpers (adopcion/donante/alerta)", ANCLA_HELPERS, NUEVO_HELPERS),
    ("adopcion_registrar", ANCLA_ADOPCION_REGISTRAR, NUEVO_ADOPCION_REGISTRAR),
    ("adopcion_listar", ANCLA_ADOPCION_LISTAR, NUEVO_ADOPCION_LISTAR),
    ("donante_agregar", ANCLA_DONANTE_AGREGAR, NUEVO_DONANTE_AGREGAR),
    ("donante_listar", ANCLA_DONANTE_LISTAR, NUEVO_DONANTE_LISTAR),
    ("donante_total_recaudado", ANCLA_DONANTE_TOTAL, NUEVO_DONANTE_TOTAL),
    ("alerta_registrar", ANCLA_ALERTA_REGISTRAR, NUEVO_ALERTA_REGISTRAR),
    ("alerta_listar", ANCLA_ALERTA_LISTAR, NUEVO_ALERTA_LISTAR),
    ("alerta_pendientes", ANCLA_ALERTA_PENDIENTES, NUEVO_ALERTA_PENDIENTES),
    ("alerta_marcar_atendida", ANCLA_ALERTA_MARCAR, NUEVO_ALERTA_MARCAR),
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

    backup = DB_C.with_suffix(".c.bak_adopciones_donantes_alertas")
    shutil.copy(DB_C, backup)

    for nombre, ancla, nuevo in REEMPLAZOS:
        contenido = contenido.replace(ancla, nuevo, 1)

    DB_C.write_text(contenido, encoding="utf-8")

    print(f"  {DB_C}: Adopciones, Donantes y Alertas de Sensores migrados a SQL Server via ODBC.")
    print(f"  Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO (si no lo has hecho ya):")
    print("  1. Crea estas 3 tablas en SQL Studio Portal (db_ace27e_pawos):")
    print()
    print("     CREATE TABLE adopciones (")
    print("         id INT IDENTITY(1,1) PRIMARY KEY,")
    print("         mascota_id INT NOT NULL,")
    print("         adoptante_nombre VARCHAR(64) NOT NULL,")
    print("         adoptante_contacto VARCHAR(64) NULL,")
    print("         fecha_adopcion VARCHAR(16) NOT NULL")
    print("     );")
    print()
    print("     CREATE TABLE donantes (")
    print("         id INT IDENTITY(1,1) PRIMARY KEY,")
    print("         nombre VARCHAR(64) NOT NULL,")
    print("         contacto VARCHAR(64) NULL,")
    print("         monto FLOAT NOT NULL,")
    print("         fecha VARCHAR(16) NOT NULL")
    print("     );")
    print()
    print("     CREATE TABLE alertas_sensores (")
    print("         id INT IDENTITY(1,1) PRIMARY KEY,")
    print("         animal_id VARCHAR(32) NOT NULL,")
    print("         tipo VARCHAR(32) NOT NULL,")
    print("         detalle VARCHAR(128) NULL,")
    print("         valor FLOAT NOT NULL,")
    print("         fecha_hora VARCHAR(24) NOT NULL,")
    print("         atendida INT NOT NULL DEFAULT 0")
    print("     );")
    print()
    print("  2. make gui")
    print("  3. Prueba desde PawOS: registrar una adopcion (y confirma que la")
    print("     mascota queda en 'adoptado'), agregar un donante (y ver el total")
    print("     recaudado), y registrar/marcar atendida una alerta de sensor.")


if __name__ == "__main__":
    main()
