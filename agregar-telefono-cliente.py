#!/usr/bin/env python3
"""
agregar-telefono-cliente.py

Primer paso para la funcion de recordatorios de citas por correo y
WhatsApp: agrega un campo de telefono a los Clientes, y una columna
para vincular (opcionalmente) una vacuna/cita con el Cliente al que
hay que avisarle.

Toca:
  - src/db/db.h: struct Cliente gana el campo "telefono"; la firma de
    cliente_registrar() gana el parametro "telefono".
  - src/db/db.c: dos migraciones nuevas (clientes.telefono,
    vacunas.cliente_id); cliente_registrar() guarda el telefono;
    cliente_autenticar() lo lee de vuelta.
  - src/main_gtk.c: el formulario "Crear cuenta de Cliente" gana el
    campo "Telefono (WhatsApp)".

No agrega todavia el selector de Cliente en Agenda de Vacunas ni el
envio real -- eso viene en los siguientes pasos.

Uso: parado en la raiz del repo:
    python3 agregar-telefono-cliente.py
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"

# ---------------------------------------------------------------
# db.h
# ---------------------------------------------------------------
ANCLA_H_STRUCT = """typedef struct {
    int        id;
    char       correo[128];
    char       nombre[64];
    RolCliente rol;
} Cliente;"""
NUEVO_H_STRUCT = """typedef struct {
    int        id;
    char       correo[128];
    char       nombre[64];
    char       telefono[32];  /* numero de WhatsApp, opcional */
    RolCliente rol;
} Cliente;"""

ANCLA_H_DECL = "int  cliente_registrar(const char *correo, const char *password, const char *nombre, RolCliente rol);"
NUEVO_H_DECL = "int  cliente_registrar(const char *correo, const char *password, const char *nombre, const char *telefono, RolCliente rol);"

# ---------------------------------------------------------------
# db.c
# ---------------------------------------------------------------
ANCLA_C_MIGRACIONES = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN rol INTEGER NOT NULL DEFAULT 0;", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE usuarios ADD COLUMN foto_base64 TEXT DEFAULT '';", NULL, NULL, NULL);
    return 0;
}"""
NUEVO_C_MIGRACIONES = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN rol INTEGER NOT NULL DEFAULT 0;", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE usuarios ADD COLUMN foto_base64 TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN telefono TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN cliente_id INTEGER;", NULL, NULL, NULL);
    return 0;
}"""

ANCLA_C_REGISTRAR = """int cliente_registrar(const char *correo, const char *password, const char *nombre, RolCliente rol) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    const char *sql = "INSERT INTO clientes (correo, password, nombre, rol) VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(st, 3, nombre, -1, SQLITE_STATIC);
    sqlite3_bind_int(st, 4, (int)rol);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""
NUEVO_C_REGISTRAR = """int cliente_registrar(const char *correo, const char *password, const char *nombre, const char *telefono, RolCliente rol) {
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
}"""

ANCLA_C_AUTENTICAR = """int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
    const char *sql = "SELECT id, nombre, password, rol FROM clientes WHERE correo=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int id = sqlite3_column_int(st, 0);
        const unsigned char *nombre = sqlite3_column_text(st, 1);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 2);
        int rol = sqlite3_column_int(st, 3);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (out) {
                    out->id = id;
                    snprintf(out->correo, sizeof(out->correo), "%s", correo);
                    snprintf(out->nombre, sizeof(out->nombre), "%s", nombre ? (const char *)nombre : "");
                    out->rol = (RolCliente)rol;
                }
                ok = 0;
            }
        }
    }"""
NUEVO_C_AUTENTICAR = """int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
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
    }"""

# ---------------------------------------------------------------
# main_gtk.c
# ---------------------------------------------------------------
ANCLA_GTK_CAMPOS = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_correo = gtk_entry_new();
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);

    GtkWidget *e_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(e_rol), 0);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Tu rol en tu organizacion:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_rol, 1, 3, 1, 1);"""
NUEVO_GTK_CAMPOS = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_correo = gtk_entry_new();
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);

    GtkWidget *e_telefono = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(e_telefono), GTK_INPUT_PURPOSE_PHONE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_telefono), "Ej: 50412345678 (con codigo de pais)");

    GtkWidget *e_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(e_rol), 0);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Telefono (WhatsApp):"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_telefono, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Tu rol en tu organizacion:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_rol, 1, 4, 1, 1);"""

ANCLA_GTK_ACEPTAR = """    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *correo = gtk_entry_get_text(GTK_ENTRY(e_correo));
        const char *password = gtk_entry_get_text(GTK_ENTRY(e_password));
        const gchar *rol_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_rol));
        RolCliente rol_elegido = rol_id_texto ? (RolCliente)atoi(rol_id_texto) : ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, rol_elegido) == 0
                && cliente_autenticar(correo, password, cliente_out) == 0) {"""
NUEVO_GTK_ACEPTAR = """    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *correo = gtk_entry_get_text(GTK_ENTRY(e_correo));
        const char *password = gtk_entry_get_text(GTK_ENTRY(e_password));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(e_telefono));
        const gchar *rol_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_rol));
        RolCliente rol_elegido = rol_id_texto ? (RolCliente)atoi(rol_id_texto) : ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, telefono, rol_elegido) == 0
                && cliente_autenticar(correo, password, cliente_out) == 0) {"""


def main():
    archivos = [
        (ARCHIVO_DB_H, [
            (ANCLA_H_STRUCT, NUEVO_H_STRUCT, "struct Cliente"),
            (ANCLA_H_DECL, NUEVO_H_DECL, "declaracion cliente_registrar"),
        ]),
        (ARCHIVO_DB_C, [
            (ANCLA_C_MIGRACIONES, NUEVO_C_MIGRACIONES, "migraciones"),
            (ANCLA_C_REGISTRAR, NUEVO_C_REGISTRAR, "cliente_registrar"),
            (ANCLA_C_AUTENTICAR, NUEVO_C_AUTENTICAR, "cliente_autenticar"),
        ]),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_CAMPOS, NUEVO_GTK_CAMPOS, "campos del formulario"),
            (ANCLA_GTK_ACEPTAR, NUEVO_GTK_ACEPTAR, "manejo del boton Crear cuenta"),
        ]),
    ]

    contenidos = {}
    for ruta, pares in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        for ancla, _nuevo, nombre in pares:
            if contenido.count(ancla) != 1:
                print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
                print("       No se cambio nada.")
                sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, pares in archivos:
        contenido = contenidos[ruta]
        for ancla, nuevo, _nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak")
        print(f"Backup creado: {ruta}.bak")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Ahora compila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all   (el CLI usa la misma db.c/db.h, debe seguir compilando)")


if __name__ == "__main__":
    main()
