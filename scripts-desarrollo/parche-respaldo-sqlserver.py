#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-respaldo-sqlserver.py

Agrega a db.c / db.h la funcion respaldo_guardar(), que inserta una
copia de una tabla (en texto CSV) en la tabla "respaldos" del SQL Server
remoto (SmarterASP), con el mismo patron ODBC del resto de db.c.

IMPORTANTE -- antes de correr esto, crea la tabla en el SQL Server
remoto (misma herramienta que usaste para las otras tablas):

   CREATE TABLE respaldos (
       id INT IDENTITY(1,1) PRIMARY KEY,
       fecha VARCHAR(20) NOT NULL,
       tabla VARCHAR(40) NOT NULL,
       contenido VARCHAR(MAX) NULL
   );

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-respaldo-sqlserver.py
"""
import shutil
import sys
from pathlib import Path

DB_C = Path("src/db/db.c")
DB_H = Path("src/db/db.h")

ANCLA_C = "int mascota_listar_disponibles(Mascota **out, int *n) {\n"

NUEVO_C = '''/* ---------- Respaldos en SQL Server ----------
 * Guarda el contenido (texto CSV) de una tabla en la tabla remota
 * "respaldos". "fecha" es el sello de ese respaldo (todas las tablas
 * de un mismo respaldo comparten la misma fecha). */
int respaldo_guardar(const char *fecha, const char *tabla, const char *contenido) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "INSERT INTO respaldos (fecha, tabla, contenido) VALUES (?,?,?);";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    const char *texto = contenido ? contenido : "";
    SQLLEN len_fecha = SQL_NTS, len_tabla = SQL_NTS, len_texto = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 20, 0, (SQLPOINTER)fecha, 0, &len_fecha);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 40, 0, (SQLPOINTER)tabla, 0, &len_tabla);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_LONGVARCHAR, (SQLULEN)strlen(texto), 0, (SQLPOINTER)texto, 0, &len_texto);
    int ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

int mascota_listar_disponibles(Mascota **out, int *n) {
'''

ANCLA_H = "int  cliente_obtener_foto(int id, char **out_foto_base64); /* out_foto_base64: liberar con free() */\n"
NUEVO_H = (
    ANCLA_H
    + "int  respaldo_guardar(const char *fecha, const char *tabla, const char *contenido); /* copia de una tabla (CSV) en la tabla remota respaldos */\n"
)


def main():
    if not DB_C.exists() or not DB_H.exists():
        print("ERROR: no se encontro src/db/db.c o src/db/db.h. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido_c = DB_C.read_text(encoding="utf-8")
    contenido_h = DB_H.read_text(encoding="utf-8")

    for nombre, texto, ancla in (("db.c", contenido_c, ANCLA_C), ("db.h", contenido_h, ANCLA_H)):
        apariciones = texto.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla esperada en {nombre} (puede que ya este parchado, o falta aplicar parche-clientes-sqlserver.py).")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla aparece mas de una vez en {nombre}, no es seguro parchar.")
            sys.exit(1)

    backup_c = DB_C.with_suffix(".bak_respaldo")
    backup_h = DB_H.with_suffix(".bak_respaldo")
    shutil.copy(DB_C, backup_c)
    shutil.copy(DB_H, backup_h)

    DB_C.write_text(contenido_c.replace(ANCLA_C, NUEVO_C, 1), encoding="utf-8")
    DB_H.write_text(contenido_h.replace(ANCLA_H, NUEVO_H, 1), encoding="utf-8")

    print(f"  db.c: agregada respaldo_guardar(). Respaldo en {backup_c}")
    print(f"  db.h: agregada la declaracion. Respaldo en {backup_h}")
    print()
    print("SIGUIENTE PASO (despues de crear la tabla 'respaldos' en SmarterASP):")
    print("  make archivos-gui")
    print("  ./pawos-archivos-gui")


if __name__ == "__main__":
    main()
