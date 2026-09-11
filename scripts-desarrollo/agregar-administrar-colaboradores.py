#!/usr/bin/env python3
"""
agregar-administrar-colaboradores.py

Agrega una pantalla nueva "Administrar Colaboradores", visible solo
para el rol Administrador, para crear cuentas de Veterinario/
Voluntario/Administrador desde el propio programa (antes no habia
ninguna forma de hacer esto sin tocar la base de datos a mano).
Incluye una foto opcional por colaborador, guardada como texto
base64 dentro de la base de datos (no como archivo aparte en disco).

Requisito: correr DESPUES de agregar-asistente-bienvenida.py (usa la
funcion usuario_registrar() que ese script agrego, y le cambia la
firma para agregarle el parametro de la foto).

Uso: parado en la raiz del repo:
    python3 agregar-administrar-colaboradores.py

Hace backup antes de tocar cada archivo, y aborta sin cambiar nada si
algun texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"

# ---------------------------------------------------------------
# db.h
# ---------------------------------------------------------------
ANCLA_DBH_STRUCT = """/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios"."""
NUEVO_DBH_STRUCT = """/* Datos basicos de un Colaborador (tabla "usuarios"), sin la
 * contrasena -- se usa para listarlos en la pantalla "Administrar
 * Colaboradores" (solo Administrador). */
typedef struct {
    int  id;
    char username[32];
    int  rol;
} UsuarioInfo;

/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios"."""

ANCLA_DBH_DECL = """int  usuario_autenticar(const char *username, const char *password, int *rol_out);
int  usuario_registrar(const char *username, const char *password, int rol);
int  existe_admin(void);"""
NUEVO_DBH_DECL = """int  usuario_autenticar(const char *username, const char *password, int *rol_out);
int  usuario_registrar(const char *username, const char *password, int rol, const char *foto_base64);
int  existe_admin(void);
int  usuario_listar(UsuarioInfo **out, int *n);"""

# ---------------------------------------------------------------
# db.c
# ---------------------------------------------------------------
ANCLA_DBC_MIGRACION = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN rol INTEGER NOT NULL DEFAULT 0;", NULL, NULL, NULL);
    return 0;
}"""
NUEVO_DBC_MIGRACION = """    sqlite3_exec(g_db, "ALTER TABLE vacunas ADD COLUMN observaciones TEXT DEFAULT '';", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE clientes ADD COLUMN rol INTEGER NOT NULL DEFAULT 0;", NULL, NULL, NULL);
    sqlite3_exec(g_db, "ALTER TABLE usuarios ADD COLUMN foto_base64 TEXT DEFAULT '';", NULL, NULL, NULL);
    return 0;
}"""

ANCLA_DBC_FUNCIONES = """/* Crea un usuario nuevo en la tabla "usuarios" (Colaboradores:
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
NUEVO_DBC_FUNCIONES = """/* Crea un usuario nuevo en la tabla "usuarios" (Colaboradores:
 * Administrador/Veterinario/Voluntario) con la contrasena ya
 * hasheada. "foto_base64" es opcional (puede ser "" o NULL) -- se
 * guarda tal cual, como texto, dentro de la misma base de datos, en
 * vez de como un archivo aparte en disco. La usa tanto el asistente
 * de bienvenida (para el primer Administrador) como la pantalla
 * "Administrar Colaboradores". */
int usuario_registrar(const char *username, const char *password, int rol, const char *foto_base64) {
    char hash[128];
    pawos_hash_password(password, hash, sizeof(hash));
    const char *sql = "INSERT INTO usuarios (username, password, rol, foto_base64) VALUES (?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(st, 3, rol);
    sqlite3_bind_text(st, 4, foto_base64 ? foto_base64 : "", -1, SQLITE_STATIC);
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

/* Lista todos los Colaboradores (id, usuario, rol -- sin contrasena
 * ni foto, para no cargar de mas) para la pantalla "Administrar
 * Colaboradores". */
int usuario_listar(UsuarioInfo **out, int *n) {
    const char *sql = "SELECT id, username, rol FROM usuarios ORDER BY rol, username;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 8, cnt = 0;
    UsuarioInfo *arr = malloc(sizeof(UsuarioInfo) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(UsuarioInfo) * cap); }
        UsuarioInfo *u = &arr[cnt++];
        u->id = sqlite3_column_int(st, 0);
        snprintf(u->username, sizeof(u->username), "%s", (const char *)sqlite3_column_text(st, 1));
        u->rol = sqlite3_column_int(st, 2);
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Clientes (publico externo) ---------------- */"""

# ---------------------------------------------------------------
# main_gtk.c -- actualizar la llamada del asistente (nueva firma)
# ---------------------------------------------------------------
ANCLA_GTK_LLAMADA_ASISTENTE = """        if (usuario_registrar(usuario_copia, pass1_copia, ROL_ADMIN) == 0) {"""
NUEVO_GTK_LLAMADA_ASISTENTE = """        if (usuario_registrar(usuario_copia, pass1_copia, ROL_ADMIN, "") == 0) {"""

# ---------------------------------------------------------------
# main_gtk.c -- pantalla nueva, insertada antes de
# construir_ventana_principal
# ---------------------------------------------------------------
ANCLA_GTK_VENTANA = """static void construir_ventana_principal(Rol rol, const char *usuario) {"""
NUEVO_GTK_VENTANA = """/* ---------------- Administrar Colaboradores (solo Admin) ---------------- */

static const char *nombre_rol_colaborador(int rol) {
    switch (rol) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        default: return "Voluntario";
    }
}

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
} ContextoColaboradores;

static void cargar_colaboradores(ContextoColaboradores *ctx) {
    gtk_list_store_clear(ctx->store);
    UsuarioInfo *usuarios;
    int n;
    if (usuario_listar(&usuarios, &n) != 0) return;
    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            0, usuarios[i].username,
            1, nombre_rol_colaborador(usuarios[i].rol),
            -1);
    }
    free(usuarios);
}

/* referencias[0] = GtkImage de vista previa, referencias[1] = ventana
 * padre (para centrar el selector de archivos encima). El base64 de
 * la foto elegida queda guardado como dato asociado a la imagen de
 * vista previa (g_object_set_data_full), para leerlo despues al
 * guardar el formulario completo. */
static void on_elegir_foto_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWidget **referencias = (GtkWidget **)datos;
    GtkWidget *dialogo = gtk_file_chooser_dialog_new(
        "Elegir foto", GTK_WINDOW(referencias[1]), GTK_FILE_CHOOSER_ACTION_OPEN,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Elegir", GTK_RESPONSE_ACCEPT,
        NULL);

    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Imagenes");
    gtk_file_filter_add_mime_type(filtro, "image/png");
    gtk_file_filter_add_mime_type(filtro, "image/jpeg");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        char *ruta = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialogo));
        gchar *contenido = NULL;
        gsize largo = 0;
        if (ruta && g_file_get_contents(ruta, &contenido, &largo, NULL)) {
            gchar *b64 = g_base64_encode((const guchar *)contenido, largo);
            g_object_set_data_full(G_OBJECT(referencias[0]), "foto_base64", b64, g_free);

            GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
            if (gdk_pixbuf_loader_write(loader, (const guchar *)contenido, largo, NULL)) {
                gdk_pixbuf_loader_close(loader, NULL);
                GdkPixbuf *pixbuf = gdk_pixbuf_loader_get_pixbuf(loader);
                if (pixbuf) {
                    GdkPixbuf *escalado = gdk_pixbuf_scale_simple(pixbuf, 64, 64, GDK_INTERP_BILINEAR);
                    gtk_image_set_from_pixbuf(GTK_IMAGE(referencias[0]), escalado);
                    g_object_unref(escalado);
                }
            }
            g_object_unref(loader);
            g_free(contenido);
        }
        g_free(ruta);
    }
    gtk_widget_destroy(dialogo);
}

static void mostrar_formulario_nuevo_colaborador(ContextoColaboradores *ctx) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Nuevo Colaborador", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Crear", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
    gtk_container_add(GTK_CONTAINER(area), caja);

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

    GtkWidget *lbl_rol = gtk_label_new("Rol:");
    gtk_widget_set_halign(lbl_rol, GTK_ALIGN_END);
    GtkWidget *combo_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "0", "Administrador");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "1", "Veterinario");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "2", "Voluntario");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_rol), 2);
    gtk_grid_attach(GTK_GRID(grid), lbl_rol, 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), combo_rol, 1, 2, 1, 1);

    GtkWidget *lbl_foto = gtk_label_new("Foto:");
    gtk_widget_set_halign(lbl_foto, GTK_ALIGN_END);
    GtkWidget *caja_foto = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *imagen_preview = gtk_image_new_from_icon_name("avatar-default-symbolic", GTK_ICON_SIZE_DIALOG);
    GtkWidget *btn_foto = gtk_button_new_with_label("Elegir foto... (opcional)");
    gtk_box_pack_start(GTK_BOX(caja_foto), imagen_preview, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_foto), btn_foto, FALSE, FALSE, 0);
    gtk_grid_attach(GTK_GRID(grid), lbl_foto, 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), caja_foto, 1, 3, 1, 1);

    GtkWidget *referencias_foto[2];
    referencias_foto[0] = imagen_preview;
    referencias_foto[1] = dialogo;
    g_signal_connect(btn_foto, "clicked", G_CALLBACK(on_elegir_foto_clicked), referencias_foto);

    gtk_entry_set_activates_default(GTK_ENTRY(entrada_user), TRUE);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada_pass), TRUE);
    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_ACCEPT);

    gtk_widget_show_all(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

    if (respuesta == GTK_RESPONSE_ACCEPT) {
        const char *usuario = gtk_entry_get_text(GTK_ENTRY(entrada_user));
        const char *pass = gtk_entry_get_text(GTK_ENTRY(entrada_pass));
        const char *rol_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(combo_rol));
        int rol = rol_texto ? atoi(rol_texto) : 2;
        const char *foto_b64 = (const char *)g_object_get_data(G_OBJECT(imagen_preview), "foto_base64");

        if (usuario[0] == '\\0' || strlen(pass) < 4) {
            gtk_widget_destroy(dialogo);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Usuario invalido o contrasena muy corta (minimo 4 caracteres).", TRUE);
            return;
        }

        gboolean ok = (usuario_registrar(usuario, pass, rol, foto_b64 ? foto_b64 : "") == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Colaborador creado correctamente.", FALSE);
            cargar_colaboradores(ctx);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo crear (ese usuario ya existe).", TRUE);
        }
        return;
    }
    gtk_widget_destroy(dialogo);
}

static void on_agregar_colaborador_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    mostrar_formulario_nuevo_colaborador((ContextoColaboradores *)datos);
}

static void abrir_pantalla_administrar_colaboradores(GtkWindow *padre, Rol rol) {
    if (rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Requiere rol Administrador.", TRUE);
        return;
    }

    ContextoColaboradores *ctx = g_malloc0(sizeof(ContextoColaboradores));

    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    ctx->ventana = ventana;
    gtk_window_set_title(GTK_WINDOW(ventana), "Administrar Colaboradores");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 420, 420);
    gtk_window_set_transient_for(GTK_WINDOW(ventana), padre);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER_ON_PARENT);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 14);
    g_signal_connect(ventana, "destroy", G_CALLBACK(g_free), ctx);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    ctx->store = gtk_list_store_new(2, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview),
        gtk_tree_view_column_new_with_attributes("Usuario", gtk_cell_renderer_text_new(), "text", 0, NULL));
    gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview),
        gtk_tree_view_column_new_with_attributes("Rol", gtk_cell_renderer_text_new(), "text", 1, NULL));

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    cargar_colaboradores(ctx);

    GtkWidget *btn_agregar = gtk_button_new_with_label("+ Agregar Colaborador");
    gtk_box_pack_start(GTK_BOX(caja), btn_agregar, FALSE, FALSE, 0);
    g_signal_connect(btn_agregar, "clicked", G_CALLBACK(on_agregar_colaborador_clicked), ctx);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

    gtk_widget_show_all(ventana);
}

static void on_administrar_colaboradores_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_administrar_colaboradores(GTK_WINDOW(d->ventana_principal), d->rol);
}

static void construir_ventana_principal(Rol rol, const char *usuario) {"""

# ---------------------------------------------------------------
# main_gtk.c -- agregar el modulo 10 a los arreglos existentes
# ---------------------------------------------------------------
ANCLA_GTK_NOMBRES = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
    };"""
NUEVO_GTK_NOMBRES = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
    };"""

ANCLA_GTK_ICONOS = """    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
    };"""
NUEVO_GTK_ICONOS = """    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
        "\\xF0\\x9F\\x91\\xA5", /* people */
    };"""

ANCLA_GTK_CATEGORIAS = """    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
    };"""
NUEVO_GTK_CATEGORIAS = """    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion",
    };"""

ANCLA_GTK_MANEJADORES = """    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
    };
    const int total_modulos = 9;"""
NUEVO_GTK_MANEJADORES = """    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
    };
    const int total_modulos = 10;"""

ANCLA_GTK_GATING = """        gboolean bloqueado_voluntario = (i == 3 || i == 4);           /* Donantes, Reportes */
        gboolean bloqueado_no_admin   = (i == 5 || i == 6);           /* Procesos, Memoria */"""
NUEVO_GTK_GATING = """        gboolean bloqueado_voluntario = (i == 3 || i == 4);           /* Donantes, Reportes */
        gboolean bloqueado_no_admin   = (i == 5 || i == 6 || i == 9); /* Procesos, Memoria, Administrar Colaboradores */"""


def main():
    archivos = [
        (ARCHIVO_DB_H, [
            (ANCLA_DBH_STRUCT, NUEVO_DBH_STRUCT, "struct UsuarioInfo"),
            (ANCLA_DBH_DECL, NUEVO_DBH_DECL, "declaraciones"),
        ], ".bak5"),
        (ARCHIVO_DB_C, [
            (ANCLA_DBC_MIGRACION, NUEVO_DBC_MIGRACION, "migracion foto_base64"),
            (ANCLA_DBC_FUNCIONES, NUEVO_DBC_FUNCIONES, "usuario_registrar/usuario_listar"),
        ], ".bak5"),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_LLAMADA_ASISTENTE, NUEVO_GTK_LLAMADA_ASISTENTE, "llamada del asistente"),
            (ANCLA_GTK_VENTANA, NUEVO_GTK_VENTANA, "pantalla Administrar Colaboradores"),
            (ANCLA_GTK_NOMBRES, NUEVO_GTK_NOMBRES, "nombres_modulos"),
            (ANCLA_GTK_ICONOS, NUEVO_GTK_ICONOS, "iconos_modulos"),
            (ANCLA_GTK_CATEGORIAS, NUEVO_GTK_CATEGORIAS, "categorias_modulos"),
            (ANCLA_GTK_MANEJADORES, NUEVO_GTK_MANEJADORES, "manejadores/total_modulos"),
            (ANCLA_GTK_GATING, NUEVO_GTK_GATING, "gating de botones"),
        ], ".bak11"),
    ]

    # Validar todo antes de escribir nada.
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
                print("       Puede que agregar-asistente-bienvenida.py no se haya aplicado todavia,")
                print("       o que el archivo ya haya sido modificado. No se cambio nada.")
                sys.exit(1)

    for ruta, pares, backup_sufijo in archivos:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        for ancla, nuevo, nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + backup_sufijo)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta}: OK (backup en {ruta}{backup_sufijo})")

    print("")
    print("Listo. Ahora:  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
