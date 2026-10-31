#!/usr/bin/env python3
"""
parche-eliminar-mascota.py

Arregla "Eliminar" en Gestion de Mascotas cuando la mascota tiene vacunas,
solicitudes de adopcion o adopciones registradas (antes fallaba por esas filas
dependientes).

  - Antes de eliminar, cuenta lo que depende de la mascota.
  - Si no hay nada, elimina como siempre.
  - Si hay algo, la confirmacion lo dice ("Tiene 2 vacunas, 1 solicitud ...
    tambien se van a borrar") y, si se acepta, borra todo en una sola
    transaccion (si algo falla, no se borra nada).

Agrega a db.c/db.h: mascota_contar_dependencias() y mascota_eliminar_completa().
mascota_eliminar() NO se toca.

Uso (parado en la raiz del repo):
    python3 parche-eliminar-mascota.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
MARCA = "mascota_eliminar_completa"

DB_FUNC = r"""static int api_contar_filas(SQLHDBC hdbc, const char *sql, int id) {
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) return -1;
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int total = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        SQLINTEGER n = 0;
        SQLLEN ind = 0;
        SQLGetData(hstmt, 1, SQL_C_LONG, &n, 0, &ind);
        total = (int)n;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    return total;
}

int mascota_contar_dependencias(int id, int *vacunas, int *solicitudes, int *adopciones) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    int v = api_contar_filas(hdbc, "SELECT COUNT(*) FROM vacunas WHERE mascota_id=?;", id);
    int s = api_contar_filas(hdbc, "SELECT COUNT(*) FROM solicitudes_adopcion WHERE mascota_id=?;", id);
    int a = api_contar_filas(hdbc, "SELECT COUNT(*) FROM adopciones WHERE mascota_id=?;", id);
    api_desconectar(henv, hdbc);
    if (v < 0 || s < 0 || a < 0) return -1;
    if (vacunas) *vacunas = v;
    if (solicitudes) *solicitudes = s;
    if (adopciones) *adopciones = a;
    return 0;
}

/* Borra la mascota y todo lo que depende de ella en UNA transaccion. */
int mascota_eliminar_completa(int id) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    static const char *sqls[] = {
        "DELETE FROM vacunas WHERE mascota_id=?;",
        "DELETE FROM solicitudes_adopcion WHERE mascota_id=?;",
        "DELETE FROM adopciones WHERE mascota_id=?;",
        "DELETE FROM mascotas WHERE id=?;"
    };
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_OFF, 0);
    int ok = 0;
    for (int i = 0; i < 4 && ok == 0; i++) {
        SQLHSTMT hstmt;
        if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) { ok = -1; break; }
        SQLPrepare(hstmt, (SQLCHAR *)sqls[i], SQL_NTS);
        SQLINTEGER id_val = id;
        SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
        if (!SQL_SUCCEEDED(SQLExecute(hstmt))) ok = -1;
        SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    }
    SQLEndTran(SQL_HANDLE_DBC, hdbc, ok == 0 ? SQL_COMMIT : SQL_ROLLBACK);
    SQLSetConnectAttr(hdbc, SQL_ATTR_AUTOCOMMIT, (SQLPOINTER)SQL_AUTOCOMMIT_ON, 0);
    api_desconectar(henv, hdbc);
    return ok;
}

int mascota_eliminar(int id) {"""

GTK_CONFIRMAR_VIEJO = r"""    GtkWidget *confirmar = gtk_message_dialog_new(
        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_YES_NO,
        "Esta seguro que desea eliminar la mascota con ID %d?\nEsta accion no se puede deshacer.", id);"""

GTK_CONFIRMAR_NUEVO = r"""    int n_vac = 0, n_sol = 0, n_ado = 0;
    int n_dep = 0;
    if (mascota_contar_dependencias(id, &n_vac, &n_sol, &n_ado) == 0)
        n_dep = n_vac + n_sol + n_ado;
    char texto_confirmar[512];
    if (n_dep > 0) {
        snprintf(texto_confirmar, sizeof(texto_confirmar),
            "La mascota con ID %d tiene registrado: %d vacuna(s), %d solicitud(es) de adopcion y %d adopcion(es).\n"
            "Si continuas, todo eso tambien se va a borrar.\nEsta accion no se puede deshacer. Continuar?",
            id, n_vac, n_sol, n_ado);
    } else {
        snprintf(texto_confirmar, sizeof(texto_confirmar),
            "Esta seguro que desea eliminar la mascota con ID %d?\nEsta accion no se puede deshacer.", id);
    }
    GtkWidget *confirmar = gtk_message_dialog_new(
        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_YES_NO,
        "%s", texto_confirmar);"""

GTK_LLAMADA_VIEJA = "        if (mascota_eliminar(id) == 0) {"
GTK_LLAMADA_NUEVA = "        if ((n_dep > 0 ? mascota_eliminar_completa(id) : mascota_eliminar(id)) == 0) {"

CAMBIOS = {
    DB_H: [
        ("int  mascota_buscar_por_id(int id, Mascota *out);",
         "int  mascota_buscar_por_id(int id, Mascota *out);\n"
         "int  mascota_contar_dependencias(int id, int *vacunas, int *solicitudes, int *adopciones);\n"
         "int  mascota_eliminar_completa(int id);",
         "declaraciones en db.h"),
    ],
    DB_C: [
        ("int mascota_eliminar(int id) {", DB_FUNC, "mascota_eliminar en db.c"),
    ],
    GTK_C: [
        (GTK_CONFIRMAR_VIEJO, GTK_CONFIRMAR_NUEVO, "dialogo de confirmacion"),
        (GTK_LLAMADA_VIEJA, GTK_LLAMADA_NUEVA, "llamada a mascota_eliminar"),
    ],
}


def main():
    contenidos = {}
    for ruta in CAMBIOS:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if MARCA in contenidos[DB_H]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_eliminar_mascota")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_eliminar_mascota)")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
