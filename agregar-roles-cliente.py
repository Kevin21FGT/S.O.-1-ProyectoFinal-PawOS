#!/usr/bin/env python3
"""
agregar-roles-cliente.py

Agrega roles DENTRO de Clientes: Jefe, Supervisor y Administrador (de
la organizacion externa que es cliente de PawOS -- otro refugio,
veterinaria, negocio, etc.). No son los mismos roles que Colaborador
(Veterinario/Voluntario), son un nivel aparte para la cuenta de
Cliente:

  - Jefe (por defecto): lo mismo que ya habia -- ver mascotas
    disponibles, solicitar adopcion, hacer una donacion.
  - Supervisor: ademas puede ver "Mis solicitudes" (el historial de
    sus propias adopciones/donaciones ya enviadas).
  - Administrador (de su organizacion cliente, NO es el Administrador
    del refugio): ademas puede "Editar mi cuenta" (cambiar su nombre
    y/o contrasena).

El rol se elige al registrarse (formulario "Registrarme" del login de
Clientes). Se guarda como columna nueva "rol" en la tabla "clientes"
ya existente (no se crea una tabla de organizaciones aparte, para no
sobre-construir).

Requisito: correr DESPUES de agregar-login-gui.py,
agregar-clientes-colaboradores.py, agregar-boton-regresar.py y
ocultar-acceso-admin.py.

Uso: parado en la raiz del repo:
    python3 agregar-roles-cliente.py

Hace backup (.bak7 para main_gtk.c, .bak2 para db.h/db.c) antes de
tocar nada, y aborta sin cambiar nada si algun texto esperado no
aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"


# ---------------------------------------------------------------
# db.h
# ---------------------------------------------------------------

ANCLA_DBH_STRUCT = '''/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios". */
typedef struct {
    int  id;
    char correo[128];
    char nombre[64];
} Cliente;'''

NUEVO_DBH_STRUCT = '''/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios".
 *
 * "rol" aqui es el nivel del Cliente DENTRO de su propia organizacion
 * (otro refugio/veterinaria/negocio que usa PawOS) -- no tiene nada
 * que ver con los roles de Colaborador (Veterinario/Voluntario). */
typedef enum {
    ROL_CLIENTE_JEFE = 0,
    ROL_CLIENTE_SUPERVISOR = 1,
    ROL_CLIENTE_ADMIN = 2
} RolCliente;

typedef struct {
    int        id;
    char       correo[128];
    char       nombre[64];
    RolCliente rol;
} Cliente;'''

ANCLA_DBH_DECL = '''int  cliente_registrar(const char *correo, const char *password, const char *nombre);
int  cliente_autenticar(const char *correo, const char *password, Cliente *out);
int  mascota_listar_disponibles(Mascota **out, int *n);'''

NUEVO_DBH_DECL = '''int  cliente_registrar(const char *correo, const char *password, const char *nombre, RolCliente rol);
int  cliente_autenticar(const char *correo, const char *password, Cliente *out);
int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
const char *cliente_rol_nombre(RolCliente rol);
int  mascota_listar_disponibles(Mascota **out, int *n);'''


# ---------------------------------------------------------------
# db.c
# ---------------------------------------------------------------

ANCLA_DBC_SCHEMA = '''    "CREATE TABLE IF NOT EXISTS clientes ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  correo TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  nombre TEXT NOT NULL"
    ");"'''

NUEVO_DBC_SCHEMA = '''    "CREATE TABLE IF NOT EXISTS clientes ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  correo TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  nombre TEXT NOT NULL,"
    "  rol INTEGER NOT NULL DEFAULT 0"
    ");"'''

ANCLA_DBC_MIGRACION = '''    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    return 0;
}'''

NUEVO_DBC_MIGRACION = '''    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN rol INTEGER NOT NULL DEFAULT 0;", NULL, NULL, NULL);
    return 0;
}'''

ANCLA_DBC_REGISTRAR = '''int cliente_registrar(const char *correo, const char *password, const char *nombre) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    const char *sql = "INSERT INTO clientes (correo, password, nombre) VALUES (?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(st, 3, nombre, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}'''

NUEVO_DBC_REGISTRAR = '''int cliente_registrar(const char *correo, const char *password, const char *nombre, RolCliente rol) {
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
}

int cliente_actualizar(int id, const char *nombre, const char *password_nueva) {
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
}

const char *cliente_rol_nombre(RolCliente rol) {
    switch (rol) {
        case ROL_CLIENTE_ADMIN: return "Administrador";
        case ROL_CLIENTE_SUPERVISOR: return "Supervisor";
        default: return "Jefe";
    }
}'''

ANCLA_DBC_AUTENTICAR = '''int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
    const char *sql = "SELECT id, nombre, password FROM clientes WHERE correo=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, correo, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int id = sqlite3_column_int(st, 0);
        const unsigned char *nombre = sqlite3_column_text(st, 1);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 2);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (out) {
                    out->id = id;
                    snprintf(out->correo, sizeof(out->correo), "%s", correo);
                    snprintf(out->nombre, sizeof(out->nombre), "%s", nombre ? (const char *)nombre : "");
                }
                ok = 0;
            }
        }
    }
    sqlite3_finalize(st);
    return ok;
}'''

NUEVO_DBC_AUTENTICAR = '''int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
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
    }
    sqlite3_finalize(st);
    return ok;
}'''


# ---------------------------------------------------------------
# main_gtk.c
# ---------------------------------------------------------------

ANCLA_GTK_STRUCT = '''    char          nombre_cliente[64];
} ContextoCliente;'''

NUEVO_GTK_STRUCT = '''    char          nombre_cliente[64];
    int           id_cliente;
    RolCliente    rol;
} ContextoCliente;'''

ANCLA_GTK_REGISTRO = '''static gboolean mostrar_registro_cliente(char *nombre_out, size_t nombre_len) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Crear cuenta de Cliente", NULL, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Crear cuenta", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 14);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_correo = gtk_entry_new();
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);

    gtk_widget_show_all(dialogo);

    gboolean creado = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *correo = gtk_entry_get_text(GTK_ENTRY(e_correo));
        const char *password = gtk_entry_get_text(GTK_ENTRY(e_password));
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre) == 0) {
                snprintf(nombre_out, nombre_len, "%s", nombre);
                creado = TRUE;
            } else {
                mostrar_mensaje(NULL, "No se pudo crear la cuenta (el correo ya podria estar registrado).", TRUE);
            }
        } else {
            mostrar_mensaje(NULL, "Completa todos los campos.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
    return creado;
}'''

NUEVO_GTK_REGISTRO = '''static gboolean mostrar_registro_cliente(Cliente *cliente_out) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Crear cuenta de Cliente", NULL, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Crear cuenta", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 14);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *e_nombre = gtk_entry_new();
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
    gtk_grid_attach(GTK_GRID(grid), e_rol, 1, 3, 1, 1);

    gtk_widget_show_all(dialogo);

    gboolean creado = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *correo = gtk_entry_get_text(GTK_ENTRY(e_correo));
        const char *password = gtk_entry_get_text(GTK_ENTRY(e_password));
        const gchar *rol_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_rol));
        RolCliente rol_elegido = rol_id_texto ? (RolCliente)atoi(rol_id_texto) : ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, rol_elegido) == 0
                && cliente_autenticar(correo, password, cliente_out) == 0) {
                creado = TRUE;
            } else {
                mostrar_mensaje(NULL, "No se pudo crear la cuenta (el correo ya podria estar registrado).", TRUE);
            }
        } else {
            mostrar_mensaje(NULL, "Completa todos los campos.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
    return creado;
}'''

ANCLA_GTK_LOGIN_FIRMA = '''static gboolean mostrar_login_cliente(char *nombre_out, size_t nombre_len, gboolean *es_admin_out) {'''
NUEVO_GTK_LOGIN_FIRMA = '''static gboolean mostrar_login_cliente(Cliente *cliente_out, gboolean *es_admin_out) {'''

ANCLA_GTK_LOGIN_REGISTRARME = '''        if (respuesta == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            char nombre_nuevo[64] = "";
            if (mostrar_registro_cliente(nombre_nuevo, sizeof(nombre_nuevo))) {
                snprintf(nombre_out, nombre_len, "%s", nombre_nuevo);
                mostrar_mensaje(NULL, "Cuenta creada. Bienvenido a PawOS.", FALSE);
                return TRUE;
            }
            continue;
        }'''

NUEVO_GTK_LOGIN_REGISTRARME = '''        if (respuesta == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            if (mostrar_registro_cliente(cliente_out)) {
                mostrar_mensaje(NULL, "Cuenta creada. Bienvenido a PawOS.", FALSE);
                if (es_admin_out) *es_admin_out = FALSE;
                return TRUE;
            }
            continue;
        }'''

ANCLA_GTK_LOGIN_AUTH = '''        int rol_secreto = -1;
        if (usuario_autenticar(correo_ingresado, password_ingresado, &rol_secreto) == 0
            && rol_secreto == ROL_ADMIN) {
            gtk_widget_destroy(dialogo);
            snprintf(nombre_out, nombre_len, "%s", correo_ingresado);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
        }

        Cliente c;
        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, &c) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            snprintf(nombre_out, nombre_len, "%s", c.nombre);
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        intentos++;'''

NUEVO_GTK_LOGIN_AUTH = '''        int rol_secreto = -1;
        if (usuario_autenticar(correo_ingresado, password_ingresado, &rol_secreto) == 0
            && rol_secreto == ROL_ADMIN) {
            gtk_widget_destroy(dialogo);
            snprintf(cliente_out->nombre, sizeof(cliente_out->nombre), "%s", correo_ingresado);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
        }

        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, cliente_out) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        intentos++;'''

ANCLA_GTK_VENTANA = '''static void construir_ventana_cliente(const char *nombre_cliente) {
    ContextoCliente *ctx = g_malloc0(sizeof(ContextoCliente));
    snprintf(ctx->nombre_cliente, sizeof(ctx->nombre_cliente), "%s", nombre_cliente);

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS Refugio - Acceso de Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 700, 460);
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    gchar *texto_bienvenida = g_strdup_printf(
        "<span size='large' weight='bold'>\\xC2\\xA1Hola, %s!</span>", ctx->nombre_cliente);
    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), texto_bienvenida);
    g_free(texto_bienvenida);
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new("Estas son las mascotas disponibles para adopcion:");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_MASCOTAS_CLIENTE,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_INT);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_MASCOTAS_CLIENTE] = {"ID", "Nombre", "Especie", "Raza", "Edad"};
    for (int i = 0; i < N_COL_MASCOTAS_CLIENTE; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_adoptar   = gtk_button_new_with_label("Solicitar adopcion");
    GtkWidget *btn_donar     = gtk_button_new_with_label("Hacer una donacion");
    GtkWidget *btn_salir     = gtk_button_new_with_label("Cerrar sesion");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_adoptar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_donar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_salir, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_mascotas_cliente_clicked), ctx);
    g_signal_connect(btn_adoptar, "clicked", G_CALLBACK(on_solicitar_adopcion_clicked), ctx);
    g_signal_connect(btn_donar, "clicked", G_CALLBACK(on_hacer_donacion_clicked), ctx);
    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    cargar_mascotas_disponibles(ctx);
    gtk_widget_show_all(ctx->ventana);
}'''

NUEVO_GTK_VENTANA = '''/* Ver mis solicitudes: solo Supervisor y Administrador (de Cliente).
 * Filtra las adopciones/donaciones ya existentes por nombre, buscando
 * las que coinciden con el nombre de este cliente. */
static void on_ver_mis_solicitudes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoCliente *ctx = (ContextoCliente *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Mis solicitudes", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cerrar", GTK_RESPONSE_CLOSE, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 420, 360);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_container_set_border_width(GTK_CONTAINER(scroll), 10);
    gtk_container_add(GTK_CONTAINER(area), scroll);

    GtkWidget *lbl = gtk_label_new(NULL);
    gtk_label_set_line_wrap(GTK_LABEL(lbl), TRUE);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_widget_set_valign(lbl, GTK_ALIGN_START);
    gtk_container_add(GTK_CONTAINER(scroll), lbl);

    GString *texto = g_string_new(NULL);
    g_string_append(texto, "<b>Adopciones solicitadas:</b>\\n");
    Adopcion *ads; int n_ads;
    if (adopcion_listar(&ads, &n_ads) == 0) {
        int encontradas = 0;
        for (int i = 0; i < n_ads; i++) {
            if (g_strcmp0(ads[i].adoptante_nombre, ctx->nombre_cliente) == 0) {
                gchar *linea = g_markup_printf_escaped(
                    "  - Mascota #%d, %s\\n", ads[i].mascota_id, ads[i].fecha_adopcion);
                g_string_append(texto, linea);
                g_free(linea);
                encontradas++;
            }
        }
        if (encontradas == 0) g_string_append(texto, "  (ninguna todavia)\\n");
        free(ads);
    }

    g_string_append(texto, "\\n<b>Donaciones:</b>\\n");
    Donante *ds; int n_ds;
    if (donante_listar(&ds, &n_ds) == 0) {
        int encontradas = 0;
        for (int i = 0; i < n_ds; i++) {
            if (g_strcmp0(ds[i].nombre, ctx->nombre_cliente) == 0) {
                gchar *linea = g_markup_printf_escaped(
                    "  - $%.2f, %s\\n", ds[i].monto, ds[i].fecha);
                g_string_append(texto, linea);
                g_free(linea);
                encontradas++;
            }
        }
        if (encontradas == 0) g_string_append(texto, "  (ninguna todavia)\\n");
        free(ds);
    }

    gtk_label_set_markup(GTK_LABEL(lbl), texto->str);
    g_string_free(texto, TRUE);

    gtk_widget_show_all(dialogo);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

/* Editar mi cuenta: solo Administrador (de Cliente). Cambia nombre y,
 * opcionalmente, contrasena (si se deja en blanco, no se toca). */
static void on_editar_cuenta_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoCliente *ctx = (ContextoCliente *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar mi cuenta", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_nombre = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(e_nombre), ctx->nombre_cliente);
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_password), "(dejar en blanco para no cambiarla)");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nueva contrasena:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_password, 1, 1, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const char *nombre_nuevo = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *password_nueva = gtk_entry_get_text(GTK_ENTRY(e_password));
        if (nombre_nuevo[0] && cliente_actualizar(ctx->id_cliente, nombre_nuevo, password_nueva) == 0) {
            snprintf(ctx->nombre_cliente, sizeof(ctx->nombre_cliente), "%s", nombre_nuevo);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Cuenta actualizada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar la cuenta.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void construir_ventana_cliente(const Cliente *cliente) {
    ContextoCliente *ctx = g_malloc0(sizeof(ContextoCliente));
    snprintf(ctx->nombre_cliente, sizeof(ctx->nombre_cliente), "%s", cliente->nombre);
    ctx->id_cliente = cliente->id;
    ctx->rol = cliente->rol;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS Refugio - Acceso de Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 700, 460);
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    gchar *texto_bienvenida = g_strdup_printf(
        "<span size='large' weight='bold'>\\xC2\\xA1Hola, %s!</span> (%s)",
        ctx->nombre_cliente, cliente_rol_nombre(ctx->rol));
    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), texto_bienvenida);
    g_free(texto_bienvenida);
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new("Estas son las mascotas disponibles para adopcion:");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_MASCOTAS_CLIENTE,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_INT);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_MASCOTAS_CLIENTE] = {"ID", "Nombre", "Especie", "Raza", "Edad"};
    for (int i = 0; i < N_COL_MASCOTAS_CLIENTE; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_adoptar   = gtk_button_new_with_label("Solicitar adopcion");
    GtkWidget *btn_donar     = gtk_button_new_with_label("Hacer una donacion");
    GtkWidget *btn_salir     = gtk_button_new_with_label("Cerrar sesion");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_adoptar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_donar, FALSE, FALSE, 0);

    if (ctx->rol >= ROL_CLIENTE_SUPERVISOR) {
        GtkWidget *btn_historial = gtk_button_new_with_label("Ver mis solicitudes");
        gtk_box_pack_start(GTK_BOX(fila_botones), btn_historial, FALSE, FALSE, 0);
        g_signal_connect(btn_historial, "clicked", G_CALLBACK(on_ver_mis_solicitudes_clicked), ctx);
    }
    if (ctx->rol >= ROL_CLIENTE_ADMIN) {
        GtkWidget *btn_editar = gtk_button_new_with_label("Editar mi cuenta");
        gtk_box_pack_start(GTK_BOX(fila_botones), btn_editar, FALSE, FALSE, 0);
        g_signal_connect(btn_editar, "clicked", G_CALLBACK(on_editar_cuenta_clicked), ctx);
    }

    gtk_box_pack_end(GTK_BOX(fila_botones), btn_salir, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_mascotas_cliente_clicked), ctx);
    g_signal_connect(btn_adoptar, "clicked", G_CALLBACK(on_solicitar_adopcion_clicked), ctx);
    g_signal_connect(btn_donar, "clicked", G_CALLBACK(on_hacer_donacion_clicked), ctx);
    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    cargar_mascotas_disponibles(ctx);
    gtk_widget_show_all(ctx->ventana);
}'''

ANCLA_GTK_MAIN = '''        } else {
            gboolean es_admin = FALSE;
            if (mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion), &es_admin)) {
                if (es_admin) {
                    construir_ventana_principal(ROL_ADMIN, nombre_sesion);
                } else {
                    construir_ventana_cliente(nombre_sesion);
                }
                logueado = TRUE;
            }
        }'''

NUEVO_GTK_MAIN = '''        } else {
            Cliente cliente_actual;
            memset(&cliente_actual, 0, sizeof(cliente_actual));
            gboolean es_admin = FALSE;
            if (mostrar_login_cliente(&cliente_actual, &es_admin)) {
                snprintf(nombre_sesion, sizeof(nombre_sesion), "%s", cliente_actual.nombre);
                if (es_admin) {
                    construir_ventana_principal(ROL_ADMIN, nombre_sesion);
                } else {
                    construir_ventana_cliente(&cliente_actual);
                }
                logueado = TRUE;
            }
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
            print("       Puede que los scripts anteriores no se hayan aplicado todavia,")
            print("       o que el archivo ya haya sido modificado. No se cambio nada.")
            sys.exit(1)
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ruta, ruta + backup_sufijo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{nombre_archivo}: OK (backup en {ruta}{backup_sufijo})")


def main():
    aplicar(ARCHIVO_DB_H, [
        (ANCLA_DBH_STRUCT, NUEVO_DBH_STRUCT),
        (ANCLA_DBH_DECL, NUEVO_DBH_DECL),
    ], ".bak2", "src/db/db.h")

    aplicar(ARCHIVO_DB_C, [
        (ANCLA_DBC_SCHEMA, NUEVO_DBC_SCHEMA),
        (ANCLA_DBC_MIGRACION, NUEVO_DBC_MIGRACION),
        (ANCLA_DBC_REGISTRAR, NUEVO_DBC_REGISTRAR),
        (ANCLA_DBC_AUTENTICAR, NUEVO_DBC_AUTENTICAR),
    ], ".bak2", "src/db/db.c")

    aplicar(ARCHIVO_GTK, [
        (ANCLA_GTK_STRUCT, NUEVO_GTK_STRUCT),
        (ANCLA_GTK_REGISTRO, NUEVO_GTK_REGISTRO),
        (ANCLA_GTK_LOGIN_FIRMA, NUEVO_GTK_LOGIN_FIRMA),
        (ANCLA_GTK_LOGIN_REGISTRARME, NUEVO_GTK_LOGIN_REGISTRARME),
        (ANCLA_GTK_LOGIN_AUTH, NUEVO_GTK_LOGIN_AUTH),
        (ANCLA_GTK_VENTANA, NUEVO_GTK_VENTANA),
        (ANCLA_GTK_MAIN, NUEVO_GTK_MAIN),
    ], ".bak7", "src/main_gtk.c")

    print("")
    print("Listo. Ahora corre:  make clean-gui && make gui")
    print("")
    print("Al registrarte como Cliente ahora eliges tu rol (Jefe/Supervisor/")
    print("Administrador). Supervisor+ ve 'Ver mis solicitudes'; Administrador")
    print("(de Cliente) ademas ve 'Editar mi cuenta'.")


if __name__ == "__main__":
    main()
