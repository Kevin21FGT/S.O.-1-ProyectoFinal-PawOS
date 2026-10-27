#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-clientes-sqlserver.py

Migra el modulo de Clientes (login/registro del Portal de Clientes) de
SQLite local a SQL Server remoto, siguiendo EXACTAMENTE el mismo patron
ya usado para Mascotas/Vacunas/Adopciones/Donantes/Alertas (funciones
api_conectar/api_desconectar + ODBC/FreeTDS). Ademas agrega soporte de
foto de perfil (guardada como texto base64, igual que usuario_registrar
ya hace para el personal del refugio) con dos funciones nuevas:
cliente_guardar_foto() y cliente_obtener_foto().

NO toca cliente_rol_nombre() (logica pura, sin base de datos).

IMPORTANTE -- antes de correr esto:
1. Debes crear la tabla "clientes" en el SQL Server remoto (la misma
   herramienta que usaste para crear las otras tablas remotas). Usa
   exactamente este SQL:

   CREATE TABLE clientes (
       id INT IDENTITY(1,1) PRIMARY KEY,
       correo VARCHAR(128) NOT NULL UNIQUE,
       password VARCHAR(128) NOT NULL,
       nombre VARCHAR(64) NOT NULL,
       telefono VARCHAR(32) NULL,
       rol INT NOT NULL DEFAULT 0,
       foto_base64 VARCHAR(MAX) NULL
   );

2. Los clientes de prueba que ya creaste (ej. kevinfv792@gmail.com)
   estaban en la base LOCAL (SQLite) y no se migran solos -- tendras
   que volver a registrarlos desde el Portal una vez aplicado esto,
   porque ahora el registro/login habla con el SQL Server remoto.

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-clientes-sqlserver.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")
DB_H = Path("src/db/db.h")

# ---------------------------------------------------------------------
# db.c: reemplazos de cada funcion cliente_* (SQLite -> ODBC remoto)
# ---------------------------------------------------------------------

ANCLA_LISTAR = '''int cliente_listar(Cliente **out, int *n) {
    const char *sql = "SELECT id, correo, nombre, telefono, rol FROM clientes ORDER BY nombre;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 8, cnt = 0;
    Cliente *arr = malloc(sizeof(Cliente) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Cliente) * cap); }
        Cliente *c = &arr[cnt++];
        c->id = sqlite3_column_int(st, 0);
        snprintf(c->correo, sizeof(c->correo), "%s", (const char *)sqlite3_column_text(st, 1));
        snprintf(c->nombre, sizeof(c->nombre), "%s", (const char *)sqlite3_column_text(st, 2));
        const unsigned char *tel = sqlite3_column_text(st, 3);
        snprintf(c->telefono, sizeof(c->telefono), "%s", tel ? (const char *)tel : "");
        c->rol = (RolCliente)sqlite3_column_int(st, 4);
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}'''

NUEVO_LISTAR = '''/* Lee las 5 columnas comunes de "clientes" (id, correo, nombre,
 * telefono, rol) desde la fila actual de un SQLHSTMT ya posicionado
 * con SQLFetch. Igual que api_leer_fila_mascota/api_leer_fila_vacuna_base. */
static void api_leer_fila_cliente_base(SQLHSTMT hstmt, Cliente *c) {
    SQLLEN ind;
    memset(c, 0, sizeof(*c));
    SQLGetData(hstmt, 1, SQL_C_LONG, &c->id, 0, &ind);
    SQLGetData(hstmt, 2, SQL_C_CHAR, c->correo, sizeof(c->correo), &ind);
    SQLGetData(hstmt, 3, SQL_C_CHAR, c->nombre, sizeof(c->nombre), &ind);
    SQLGetData(hstmt, 4, SQL_C_CHAR, c->telefono, sizeof(c->telefono), &ind);
    if (ind == SQL_NULL_DATA) c->telefono[0] = '\\0';
    int rol_tmp = 0;
    SQLGetData(hstmt, 5, SQL_C_LONG, &rol_tmp, 0, &ind);
    c->rol = (RolCliente)rol_tmp;
}

int cliente_listar(Cliente **out, int *n) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id, correo, nombre, telefono, rol FROM clientes ORDER BY nombre;";
    if (!SQL_SUCCEEDED(SQLExecDirect(hstmt, (SQLCHAR *)sql, SQL_NTS))) {
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        api_desconectar(henv, hdbc);
        return -1;
    }
    int cap = 8, cnt = 0;
    Cliente *arr = malloc(sizeof(Cliente) * cap);
    while (SQLFetch(hstmt) == SQL_SUCCESS) {
        if (cnt >= cap) { cap *= 2; arr = realloc(arr, sizeof(Cliente) * cap); }
        api_leer_fila_cliente_base(hstmt, &arr[cnt++]);
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    *out = arr;
    *n = cnt;
    return 0;
}'''

ANCLA_REGISTRAR = '''int cliente_registrar(const char *correo, const char *password, const char *nombre, const char *telefono, RolCliente rol) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    const char *sql = "INSERT INTO clientes (correo, password, nombre, telefono, rol) VALUES (?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(st, 3, nombre, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, telefono ? telefono : "", -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 5, (int)rol);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_REGISTRAR = '''int cliente_registrar(const char *correo, const char *password, const char *nombre, const char *telefono, RolCliente rol) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "INSERT INTO clientes (correo, password, nombre, telefono, rol) VALUES (?,?,?,?,?);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len_correo = SQL_NTS, len_hash = SQL_NTS, len_nombre = SQL_NTS, len_tel = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 128, 0, (SQLPOINTER)correo, 0, &len_correo);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 128, 0, (SQLPOINTER)hash, 0, &len_hash);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 64, 0, (SQLPOINTER)nombre, 0, &len_nombre);
    const char *tel = telefono ? telefono : "";
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 32, 0, (SQLPOINTER)tel, 0, &len_tel);
    SQLINTEGER rol_val = (SQLINTEGER)rol;
    SQLBindParameter(hstmt, 5, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &rol_val, 0, NULL);
    SQLRETURN ret = SQLExecute(hstmt);
    int ok = SQL_SUCCEEDED(ret) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}'''

ANCLA_ACTUALIZAR = '''int cliente_actualizar(int id, const char *nombre, const char *password_nueva) {
    sqlite3_stmt *st;
    if (password_nueva && password_nueva[0] != '\\0') {
        char hash[128];
        pawos_hash_password(password_nueva, hash, sizeof(hash));
        if (sqlite3_prepare_v2(g_db, "UPDATE clientes SET nombre=?, password=? WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
        sqlite3_bind_text(st, 1, nombre, -1, SQLITE_STATIC);
        sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(st, 3, id);
    } else {
        if (sqlite3_prepare_v2(g_db, "UPDATE clientes SET nombre=? WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
        sqlite3_bind_text(st, 1, nombre, -1, SQLITE_STATIC);
        sqlite3_bind_int(st, 2, id);
    }
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_ACTUALIZAR = '''int cliente_actualizar(int id, const char *nombre, const char *password_nueva) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLLEN len_nombre = SQL_NTS;
    int ok;
    if (password_nueva && password_nueva[0] != '\\0') {
        char hash[128];
        pawos_hash_password(password_nueva, hash, sizeof(hash));
        const char *sql = "UPDATE clientes SET nombre=?, password=? WHERE id=?;";
        SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
        SQLLEN len_hash = SQL_NTS;
        SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 64, 0, (SQLPOINTER)nombre, 0, &len_nombre);
        SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 128, 0, (SQLPOINTER)hash, 0, &len_hash);
        SQLINTEGER id_val = id;
        SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
        ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    } else {
        const char *sql = "UPDATE clientes SET nombre=? WHERE id=?;";
        SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
        SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 64, 0, (SQLPOINTER)nombre, 0, &len_nombre);
        SQLINTEGER id_val = id;
        SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
        ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}'''

ANCLA_ROL = '''int cliente_actualizar_rol(int id, RolCliente nuevo_rol) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "UPDATE clientes SET rol=? WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, (int)nuevo_rol);
    sqlite3_bind_int(st, 2, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_ROL = '''int cliente_actualizar_rol(int id, RolCliente nuevo_rol) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE clientes SET rol=? WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER rol_val = (SQLINTEGER)nuevo_rol;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &rol_val, 0, NULL);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}'''

ANCLA_EXISTE = '''int cliente_existe(const char *correo) {
    const char *sql = "SELECT 1 FROM clientes WHERE correo=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return 0;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    int existe = (sqlite3_step(st) == SQLITE_ROW) ? 1 : 0;
    sqlite3_finalize(st);
    return existe;
}'''

NUEVO_EXISTE = '''int cliente_existe(const char *correo) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return 0;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return 0;
    }
    const char *sql = "SELECT 1 FROM clientes WHERE correo=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len_correo = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 128, 0, (SQLPOINTER)correo, 0, &len_correo);
    int existe = 0;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) existe = 1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return existe;
}'''

ANCLA_AUTENTICAR = '''int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
    const char *sql = "SELECT id, nombre, password, rol, telefono FROM clientes WHERE correo=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int id = sqlite3_column_int(st, 0);
        const unsigned char *nombre = sqlite3_column_text(st, 1);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 2);
        int rol = sqlite3_column_int(st, 3);
        const unsigned char *telefono = sqlite3_column_text(st, 4);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (out) {
                    out->id = id;
                    snprintf(out->correo, sizeof(out->correo), "%s", correo);
                    snprintf(out->nombre, sizeof(out->nombre), "%s", nombre ? (const char *)nombre : "");
                    snprintf(out->telefono, sizeof(out->telefono), "%s", telefono ? (const char *)telefono : "");
                    out->rol = (RolCliente)rol;
                }
                ok = 0;
            }
        }
    }
    sqlite3_finalize(st);
    return ok;
}'''

NUEVO_AUTENTICAR = '''int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT id, nombre, password, rol, telefono FROM clientes WHERE correo=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLLEN len_correo = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 128, 0, (SQLPOINTER)correo, 0, &len_correo);
    int ok = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        SQLLEN ind;
        int id = 0;
        char nombre[64] = "";
        char hash_guardado[128] = "";
        int rol = 0;
        char telefono[32] = "";
        SQLGetData(hstmt, 1, SQL_C_LONG, &id, 0, &ind);
        SQLGetData(hstmt, 2, SQL_C_CHAR, nombre, sizeof(nombre), &ind);
        SQLGetData(hstmt, 3, SQL_C_CHAR, hash_guardado, sizeof(hash_guardado), &ind);
        SQLGetData(hstmt, 4, SQL_C_LONG, &rol, 0, &ind);
        SQLGetData(hstmt, 5, SQL_C_CHAR, telefono, sizeof(telefono), &ind);
        if (ind == SQL_NULL_DATA) telefono[0] = '\\0';
        if (hash_guardado[0]) {
            char *resultado = crypt(password, hash_guardado);
            if (resultado && strcmp(resultado, hash_guardado) == 0) {
                if (out) {
                    out->id = id;
                    snprintf(out->correo, sizeof(out->correo), "%s", correo);
                    snprintf(out->nombre, sizeof(out->nombre), "%s", nombre);
                    snprintf(out->telefono, sizeof(out->telefono), "%s", telefono);
                    out->rol = (RolCliente)rol;
                }
                ok = 0;
            }
        }
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

/* ---------- Foto de perfil del Cliente ----------
 * Guardada como texto base64 (igual que usuario_registrar ya hace
 * para el personal del refugio), pero en una columna de la tabla
 * "clientes" en el SQL Server remoto, para que se vea desde
 * cualquier maquina que use el Portal de Clientes. */
int cliente_guardar_foto(int id, const char *foto_base64) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE clientes SET foto_base64=? WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    const char *foto = foto_base64 ? foto_base64 : "";
    SQLLEN len_foto = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_LONGVARCHAR, (SQLULEN)strlen(foto), 0, (SQLPOINTER)foto, 0, &len_foto);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

/* out_foto_base64: el llamador debe liberar con free() el resultado
 * (si no es NULL). Devuelve 0 y "" si el cliente no tiene foto. Se lee
 * en bloques con SQLGetData porque el texto puede ser grande (una
 * foto codificada en base64), a diferencia de los demas campos de
 * texto de este archivo que caben en un buffer fijo pequeno. */
int cliente_obtener_foto(int id, char **out_foto_base64) {
    *out_foto_base64 = NULL;
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT foto_base64 FROM clientes WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int ok = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        size_t cap = 8192, usado = 0;
        char *buf = malloc(cap);
        buf[0] = '\\0';
        SQLRETURN ret;
        char trozo[4096];
        SQLLEN ind;
        do {
            ret = SQLGetData(hstmt, 1, SQL_C_CHAR, trozo, sizeof(trozo), &ind);
            if (ind == SQL_NULL_DATA || !SQL_SUCCEEDED(ret)) break;
            size_t len_trozo = strlen(trozo);
            if (usado + len_trozo + 1 > cap) {
                cap = (usado + len_trozo + 1) * 2;
                buf = realloc(buf, cap);
            }
            memcpy(buf + usado, trozo, len_trozo);
            usado += len_trozo;
            buf[usado] = '\\0';
        } while (ret == SQL_SUCCESS_WITH_INFO);
        *out_foto_base64 = buf;
        ok = 0;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}'''

# ---------------------------------------------------------------------
# db.h: declaraciones nuevas
# ---------------------------------------------------------------------

ANCLA_H = "int  cliente_listar(Cliente **out, int *n);\n"
NUEVO_H = (
    "int  cliente_listar(Cliente **out, int *n);\n"
    "int  cliente_guardar_foto(int id, const char *foto_base64);\n"
    "int  cliente_obtener_foto(int id, char **out_foto_base64); /* out_foto_base64: liberar con free() */\n"
)

REEMPLAZOS_DB_C = [
    ("cliente_listar", ANCLA_LISTAR, NUEVO_LISTAR),
    ("cliente_registrar", ANCLA_REGISTRAR, NUEVO_REGISTRAR),
    ("cliente_actualizar", ANCLA_ACTUALIZAR, NUEVO_ACTUALIZAR),
    ("cliente_actualizar_rol", ANCLA_ROL, NUEVO_ROL),
    ("cliente_existe", ANCLA_EXISTE, NUEVO_EXISTE),
    ("cliente_autenticar (+ foto nueva)", ANCLA_AUTENTICAR, NUEVO_AUTENTICAR),
]


def main():
    if not DB_C.exists() or not DB_H.exists():
        print("ERROR: no se encontro src/db/db.c o src/db/db.h. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido_c = DB_C.read_text(encoding="utf-8")
    for nombre, ancla, nuevo in REEMPLAZOS_DB_C:
        apariciones = contenido_c.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en db.c (puede que ya este parchado, o el archivo cambio).")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez en db.c, no es seguro parchar.")
            sys.exit(1)

    contenido_h = DB_H.read_text(encoding="utf-8")
    apariciones_h = contenido_h.count(ANCLA_H)
    if apariciones_h == 0:
        print("ERROR: no se encontro el ancla esperada en db.h (puede que ya este parchado).")
        sys.exit(1)
    if apariciones_h > 1:
        print("ERROR: el ancla en db.h aparece mas de una vez, no es seguro parchar.")
        sys.exit(1)

    backup_c = DB_C.with_suffix(".bak_clientes_sqlserver")
    backup_h = DB_H.with_suffix(".bak_clientes_sqlserver")
    shutil.copy(DB_C, backup_c)
    shutil.copy(DB_H, backup_h)

    for nombre, ancla, nuevo in REEMPLAZOS_DB_C:
        contenido_c = contenido_c.replace(ancla, nuevo, 1)
    DB_C.write_text(contenido_c, encoding="utf-8")

    contenido_h = contenido_h.replace(ANCLA_H, NUEVO_H, 1)
    DB_H.write_text(contenido_h, encoding="utf-8")

    print(f"  db.c: {len(REEMPLAZOS_DB_C)} funciones de Cliente migradas a SQL Server remoto. Respaldo en {backup_c}")
    print(f"  db.h: agregadas declaraciones de cliente_guardar_foto/cliente_obtener_foto. Respaldo en {backup_h}")
    print()
    print("RECUERDA antes de compilar:")
    print("  1. Crear la tabla 'clientes' en el SQL Server remoto (ver el SQL en la cabecera de este script).")
    print("  2. Los clientes de prueba locales anteriores no se migran solos -- hay que volver a registrarlos.")
    print()
    print("SIGUIENTE PASO:")
    print("  make vacunas-gui   (usa db.c, recompila para confirmar que no rompio nada)")
    print("  make portal-clientes")


if __name__ == "__main__":
    main()
