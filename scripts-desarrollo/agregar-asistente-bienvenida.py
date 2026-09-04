#!/usr/bin/env python3
"""
agregar-asistente-bienvenida.py

Agrega un "asistente de bienvenida" que crea la cuenta del primer
Administrador la primera vez que se abre PawOS Refugio -- pensado
para la version que se vende/reparte como instalador .deb, NO para
la version del curso.

Como funciona:
  - db.c ya siembra automaticamente admin_refugio/veterinario1/
    voluntario1 con contrasena fija cada vez que la base de datos
    esta vacia. Eso sigue igual en la version normal ("make gui").
  - Se agrega una nueva bandera de compilacion, PAWOS_SIN_SEMILLA,
    que cuando esta definida DESACTIVA esa siembra automatica. Se usa
    solo en el nuevo target del Makefile "make gui-producto" (el que
    usa construir-deb.sh para armar el .deb).
  - En main_gtk.c, main() revisa (sin importar la bandera de
    compilacion) si ya existe algun Administrador; si no existe,
    muestra el asistente para crear uno antes de dejar entrar al
    programa. En la version del curso esto nunca se activa, porque
    siempre hay un Administrador sembrado desde el arranque.

Requisito: correr con el codigo tal como quedo despues de todos los
parches anteriores de esta sesion (diferenciar-correo-no-registrado.py
incluido).

Uso: parado en la raiz del repo:
    python3 agregar-asistente-bienvenida.py

Hace backup antes de tocar cada archivo, y aborta sin cambiar nada si
algun texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"
ARCHIVO_MAKEFILE = "Makefile"

# ---------------------------------------------------------------
# db.h
# ---------------------------------------------------------------
ANCLA_DBH = """int  usuario_autenticar(const char *username, const char *password, int *rol_out);

/* ---------- Clientes (publico externo: adoptantes y donantes) ---------- */"""
NUEVO_DBH = """int  usuario_autenticar(const char *username, const char *password, int *rol_out);
int  usuario_registrar(const char *username, const char *password, int rol);
int  existe_admin(void);

/* ---------- Clientes (publico externo: adoptantes y donantes) ---------- */"""

# ---------------------------------------------------------------
# db.c -- desactivar la siembra fija cuando se compila con
# -DPAWOS_SIN_SEMILLA, y agregar usuario_registrar()/existe_admin()
# ---------------------------------------------------------------
ANCLA_DBC_SEMILLA = """    {
        struct { const char *user; const char *pass; int rol; } semilla[] = {
            {"admin_refugio", "admin123", 0},
            {"veterinario1",  "vet123",   1},
            {"voluntario1",   "vol123",   2},
        };
        const char *sql_seed =
            "INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?,?,?);";
        for (size_t i = 0; i < sizeof(semilla) / sizeof(semilla[0]); i++) {
            char hash[128];
            pawos_hash_password(semilla[i].pass, hash, sizeof(hash));
            sqlite3_stmt *st;
            if (sqlite3_prepare_v2(g_db, sql_seed, -1, &st, NULL) == SQLITE_OK) {
                sqlite3_bind_text(st, 1, semilla[i].user, -1, SQLITE_STATIC);
                sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(st, 3, semilla[i].rol);
                sqlite3_step(st);
                sqlite3_finalize(st);
            }
        }
    }"""
NUEVO_DBC_SEMILLA = """#ifndef PAWOS_SIN_SEMILLA
    /* Solo en la version del curso (make gui normal). La version
     * "producto" (make gui-producto, la que usa construir-deb.sh)
     * se compila con -DPAWOS_SIN_SEMILLA y se salta esto por
     * completo -- en esa version, el primer Administrador lo crea
     * cada quien desde el asistente de bienvenida (main_gtk.c). */
    {
        struct { const char *user; const char *pass; int rol; } semilla[] = {
            {"admin_refugio", "admin123", 0},
            {"veterinario1",  "vet123",   1},
            {"voluntario1",   "vol123",   2},
        };
        const char *sql_seed =
            "INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?,?,?);";
        for (size_t i = 0; i < sizeof(semilla) / sizeof(semilla[0]); i++) {
            char hash[128];
            pawos_hash_password(semilla[i].pass, hash, sizeof(hash));
            sqlite3_stmt *st;
            if (sqlite3_prepare_v2(g_db, sql_seed, -1, &st, NULL) == SQLITE_OK) {
                sqlite3_bind_text(st, 1, semilla[i].user, -1, SQLITE_STATIC);
                sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
                sqlite3_bind_int(st, 3, semilla[i].rol);
                sqlite3_step(st);
                sqlite3_finalize(st);
            }
        }
    }
#endif"""

ANCLA_DBC_FUNCIONES = """/* ---------------- Clientes (publico externo) ---------------- */"""
NUEVO_DBC_FUNCIONES = """/* Crea un usuario nuevo en la tabla "usuarios" (Colaboradores:
 * Administrador/Veterinario/Voluntario) con la contrasena ya
 * hasheada -- la usa el asistente de bienvenida para crear el primer
 * Administrador en la version "producto" (ver PAWOS_SIN_SEMILLA). */
int usuario_registrar(const char *username, const char *password, int rol) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    const char *sql = "INSERT INTO usuarios (username, password, rol) VALUES (?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(st, 3, rol);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* Dice si ya existe al menos un usuario con rol Administrador (rol=0)
 * en la tabla "usuarios". El asistente de bienvenida (main_gtk.c) lo
 * usa para decidir si hace falta mostrarse: en la version del curso
 * siempre hay uno sembrado desde el arranque, asi que esto nunca
 * dispara el asistente ahi. */
int existe_admin(void) {
    const char *sql = "SELECT 1 FROM usuarios WHERE rol=0 LIMIT 1;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return 0;
    int existe = (sqlite3_step(st) == SQLITE_ROW) ? 1 : 0;
    sqlite3_finalize(st);
    return existe;
}

/* ---------------- Clientes (publico externo) ---------------- */"""

# ---------------------------------------------------------------
# main_gtk.c -- funcion del asistente + llamada en main()
# ---------------------------------------------------------------
ANCLA_GTK_FUNCION = """int main(int argc, char **argv) {"""
NUEVO_GTK_FUNCION = """/* Asistente de bienvenida: crea la cuenta del primer Administrador.
 * Solo se muestra si "existe_admin()" dice que todavia no hay
 * ninguno -- en la practica, eso solo pasa en la version "producto"
 * (compilada con -DPAWOS_SIN_SEMILLA, ver Makefile: "gui-producto"),
 * porque la version del curso siempre siembra un Administrador desde
 * el arranque. No se puede cancelar: hace falta un Administrador
 * para poder usar el programa. */
static void mostrar_asistente_bienvenida(void) {
    GtkWidget *bienvenida = gtk_message_dialog_new(
        NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_OK,
        "Bienvenido a PawOS Refugio");
    gtk_message_dialog_format_secondary_text(GTK_MESSAGE_DIALOG(bienvenida),
        "Antes de empezar, vamos a crear la cuenta de Administrador de este refugio.");
    gtk_dialog_run(GTK_DIALOG(bienvenida));
    gtk_widget_destroy(bienvenida);

    for (;;) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Crear Administrador", NULL, GTK_DIALOG_MODAL,
            "Crear cuenta", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

        GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area), caja);

        GtkWidget *titulo = gtk_label_new(NULL);
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>Cuenta de Administrador</span>");
        gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

        GtkWidget *grid = gtk_grid_new();
        gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
        gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
        gtk_box_pack_start(GTK_BOX(caja), grid, FALSE, FALSE, 0);

        GtkWidget *lbl_user = gtk_label_new("Usuario:");
        gtk_widget_set_halign(lbl_user, GTK_ALIGN_END);
        GtkWidget *entrada_user = gtk_entry_new();
        gtk_grid_attach(GTK_GRID(grid), lbl_user, 0, 0, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_user, 1, 0, 1, 1);

        GtkWidget *lbl_pass = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_pass, GTK_ALIGN_END);
        GtkWidget *entrada_pass = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass, 1, 1, 1, 1);

        GtkWidget *lbl_pass2 = gtk_label_new("Confirmar:");
        gtk_widget_set_halign(lbl_pass2, GTK_ALIGN_END);
        GtkWidget *entrada_pass2 = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass2), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass2), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass2, 0, 2, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass2, 1, 2, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_user), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_pass), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_pass2), TRUE);
        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_ACCEPT);

        gtk_widget_show_all(dialogo);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (respuesta != GTK_RESPONSE_ACCEPT) {
            gtk_widget_destroy(dialogo);
            continue;
        }

        char usuario_copia[64];
        char pass1_copia[64];
        char pass2_copia[64];
        snprintf(usuario_copia, sizeof(usuario_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_user)));
        snprintf(pass1_copia, sizeof(pass1_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_pass)));
        snprintf(pass2_copia, sizeof(pass2_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_pass2)));
        gtk_widget_destroy(dialogo);

        const char *error = NULL;
        if (usuario_copia[0] == '\\0') {
            error = "El usuario no puede estar vacio.";
        } else if (strlen(pass1_copia) < 4) {
            error = "La contrasena debe tener al menos 4 caracteres.";
        } else if (strcmp(pass1_copia, pass2_copia) != 0) {
            error = "Las contrasenas no coinciden.";
        }

        if (error) {
            mostrar_mensaje(NULL, error, TRUE);
            continue;
        }

        if (usuario_registrar(usuario_copia, pass1_copia, ROL_ADMIN) == 0) {
            mostrar_mensaje(NULL, "Cuenta de Administrador creada. Ya puedes iniciar sesion.", FALSE);
            return;
        }
        mostrar_mensaje(NULL, "No se pudo crear la cuenta (ese usuario ya existe). Intenta con otro nombre.", TRUE);
    }
}

int main(int argc, char **argv) {"""

ANCLA_GTK_LLAMADA = """    if (!memoria_inicializar()) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de memoria.\\n");
    }

    for (;;) {"""
NUEVO_GTK_LLAMADA = """    if (!memoria_inicializar()) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de memoria.\\n");
    }

    if (!existe_admin()) {
        mostrar_asistente_bienvenida();
    }

    for (;;) {"""

# ---------------------------------------------------------------
# Makefile -- nuevo target gui-producto
# ---------------------------------------------------------------
ANCLA_MAKEFILE = """gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

clean-gui:
\trm -f $(GUI_BIN)

.PHONY: gui clean-gui"""
NUEVO_MAKEFILE = """gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

# Variante para el instalador .deb ("vender el programa" - ver
# construir-deb.sh): no siembra las cuentas fijas admin_refugio/
# veterinario1/voluntario1. En su lugar, la primera vez que se abre
# el programa se muestra un asistente para crear el Administrador con
# una contrasena propia. La version del curso ("make gui" normal) no
# cambia en nada.
gui-producto: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) -DPAWOS_SIN_SEMILLA $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

clean-gui:
\trm -f $(GUI_BIN)

.PHONY: gui gui-producto clean-gui"""


def aplicar(ruta, pares, backup_sufijo):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       No se cambio nada en ningun archivo todavia.")
            sys.exit(1)

    for ancla, nuevo, nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ruta, ruta + backup_sufijo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ruta}: OK (backup en {ruta}{backup_sufijo})")


def main():
    # Primero se validan TODOS los anclas de TODOS los archivos antes
    # de escribir nada, para no dejar el repo a medias si uno falla.
    archivos = [
        (ARCHIVO_DB_H, [(ANCLA_DBH, NUEVO_DBH, "declaraciones")], ".bak4"),
        (ARCHIVO_DB_C, [
            (ANCLA_DBC_SEMILLA, NUEVO_DBC_SEMILLA, "siembra de usuarios"),
            (ANCLA_DBC_FUNCIONES, NUEVO_DBC_FUNCIONES, "usuario_registrar/existe_admin"),
        ], ".bak4"),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_FUNCION, NUEVO_GTK_FUNCION, "funcion del asistente"),
            (ANCLA_GTK_LLAMADA, NUEVO_GTK_LLAMADA, "llamada en main()"),
        ], ".bak9"),
        (ARCHIVO_MAKEFILE, [(ANCLA_MAKEFILE, NUEVO_MAKEFILE, "target gui-producto")], ".bak"),
    ]

    for ruta, pares, _ in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        for ancla, nuevo, nombre in pares:
            if contenido.count(ancla) != 1:
                print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
                print("       No se cambio nada en ningun archivo. Revisa si el codigo ya fue modificado.")
                sys.exit(1)

    for ruta, pares, backup_sufijo in archivos:
        aplicar(ruta, pares, backup_sufijo)

    print("")
    print("Listo. Para la version del curso: make clean-gui && make gui (sin cambios de comportamiento).")
    print("Para la version 'producto' (instalador .deb): make clean-gui && make gui-producto")
    print("(y actualiza construir-deb.sh para que use 'make gui-producto' en vez de 'make gui').")


if __name__ == "__main__":
    main()
