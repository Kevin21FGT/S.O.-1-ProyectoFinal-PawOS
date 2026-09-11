#!/usr/bin/env python3
"""
diferenciar-correo-no-registrado.py

En el login de Clientes, distingue dos casos que antes daban el mismo
mensaje generico ("Correo o contrasena incorrectos"):

  - El correo NO esta registrado -> "Ese correo no esta registrado."
  - El correo SI esta registrado pero la contrasena esta mal ->
    "Correo o contrasena incorrectos." (igual que antes)

Ambos casos siguen contando dentro del limite de 3 intentos.

Requisito: correr DESPUES de agregar-roles-cliente.py.

Uso: parado en la raiz del repo:
    python3 diferenciar-correo-no-registrado.py

Hace backup (.bak3 para db.h/db.c, .bak8 para main_gtk.c) antes de
tocar nada, y aborta sin cambiar nada si algun texto esperado no
aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"

ANCLA_DBH = '''int  cliente_autenticar(const char *correo, const char *password, Cliente *out);'''
NUEVO_DBH = '''int  cliente_autenticar(const char *correo, const char *password, Cliente *out);
int  cliente_existe(const char *correo);'''

ANCLA_DBC = '''int cliente_autenticar(const char *correo, const char *password, Cliente *out) {'''
NUEVO_DBC = '''/* Solo dice si el correo existe en la tabla clientes, sin revisar
 * contrasena -- se usa nada mas para mostrar un mensaje distinto en
 * el login ("correo no registrado" vs "contrasena incorrecta"). */
int cliente_existe(const char *correo) {
    const char *sql = "SELECT 1 FROM clientes WHERE correo=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return 0;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    int existe = (sqlite3_step(st) == SQLITE_ROW) ? 1 : 0;
    sqlite3_finalize(st);
    return existe;
}

int cliente_autenticar(const char *correo, const char *password, Cliente *out) {'''

ANCLA_GTK_DECLARAR = '''    int intentos = 0;
    const int max_intentos = 3;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,'''
NUEVO_GTK_DECLARAR = '''    int intentos = 0;
    const int max_intentos = 3;
    gboolean no_registrado = FALSE;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,'''

ANCLA_GTK_ERROR = '''        if (intentos > 0) {
            GtkWidget *lbl_error = gtk_label_new(NULL);
            gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
            gchar *texto_error = g_strdup_printf(
                "<span foreground='red'>Correo o contrasena incorrectos. Intento %d de %d.</span>",
                intentos, max_intentos);
            gtk_label_set_markup(GTK_LABEL(lbl_error), texto_error);
            g_free(texto_error);
            gtk_box_pack_start(GTK_BOX(caja), lbl_error, FALSE, FALSE, 0);
        }

        gtk_widget_show_all(dialogo);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (respuesta == RESPUESTA_REGISTRARME) {'''
NUEVO_GTK_ERROR = '''        if (intentos > 0) {
            GtkWidget *lbl_error = gtk_label_new(NULL);
            gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
            gchar *texto_error = no_registrado
                ? g_strdup_printf(
                    "<span foreground='red'>Ese correo no esta registrado. Intento %d de %d.</span>",
                    intentos, max_intentos)
                : g_strdup_printf(
                    "<span foreground='red'>Correo o contrasena incorrectos. Intento %d de %d.</span>",
                    intentos, max_intentos);
            gtk_label_set_markup(GTK_LABEL(lbl_error), texto_error);
            g_free(texto_error);
            gtk_box_pack_start(GTK_BOX(caja), lbl_error, FALSE, FALSE, 0);
        }

        gtk_widget_show_all(dialogo);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (respuesta == RESPUESTA_REGISTRARME) {'''

ANCLA_GTK_FALLO = '''        if (ok) {
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        intentos++;
    }'''
NUEVO_GTK_FALLO = '''        if (ok) {
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        no_registrado = !cliente_existe(correo_ingresado);
        intentos++;
    }'''


def aplicar(ruta, pares, backup_sufijo, nombre_archivo):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, nuevo in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta} no se encontro (o se encontro mas de una vez) un bloque esperado.")
            print("       Puede que agregar-roles-cliente.py no se haya aplicado todavia,")
            print("       o que el archivo ya haya sido modificado. No se cambio nada.")
            sys.exit(1)
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ruta, ruta + backup_sufijo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{nombre_archivo}: OK (backup en {ruta}{backup_sufijo})")


def main():
    aplicar(ARCHIVO_DB_H, [(ANCLA_DBH, NUEVO_DBH)], ".bak3", "src/db/db.h")
    aplicar(ARCHIVO_DB_C, [(ANCLA_DBC, NUEVO_DBC)], ".bak3", "src/db/db.c")
    aplicar(ARCHIVO_GTK, [
        (ANCLA_GTK_DECLARAR, NUEVO_GTK_DECLARAR),
        (ANCLA_GTK_ERROR, NUEVO_GTK_ERROR),
        (ANCLA_GTK_FALLO, NUEVO_GTK_FALLO),
    ], ".bak8", "src/main_gtk.c")

    print("")
    print("Listo. Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
