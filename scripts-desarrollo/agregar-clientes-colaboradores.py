#!/usr/bin/env python3
"""
agregar-clientes-colaboradores.py

Agrega el acceso de "Clientes" (publico externo: adoptantes y
donantes) separado del de "Colaboradores" (personal del refugio, el
login que ya existe con la tabla "usuarios").

Que agrega:
  - Tabla nueva "clientes" (correo, contrasena con hash, nombre) en la
    base de datos, separada de "usuarios".
  - cliente_registrar() / cliente_autenticar() en db.c/db.h, mismo
    patron de hash (crypt/SHA-512) que usuario_autenticar().
  - mascota_listar_disponibles() en db.c/db.h (solo estado=disponible).
  - En main_gtk.c: al abrir el programa, primero aparecen 2 botones
    ("Soy Colaborador" / "Soy Cliente"). Colaborador entra igual que
    ahora (usuario/contrasena, ventana principal completa). Cliente
    entra con correo/contrasena (o se registra ahi mismo si es nuevo)
    a una ventana MAS SIMPLE: solo ve las mascotas disponibles para
    adopcion, puede solicitar una adopcion o hacer una donacion -- no
    ve procesos, memoria, reportes ni nada interno del refugio.

Requisito: correr agregar-login-gui.py ANTES que este script (este
script parte de que main_gtk.c ya tiene mostrar_login_gtk()).

Uso: parado en la raiz del repo (rama con el login de Colaboradores ya
aplicado):
    python3 agregar-clientes-colaboradores.py

Hace backup automatico (.bak4) antes de tocar nada, y aborta sin
cambiar nada si algun texto esperado no aparece exactamente como se
espera en algun archivo.
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"


# ---------------------------------------------------------------
# 1) db.h
# ---------------------------------------------------------------

ANCLA_DBH_STRUCT = '''} NotaVeterinario;

/* ---------- Ciclo de vida ---------- */'''

NUEVO_DBH_STRUCT = '''} NotaVeterinario;

/* Cliente = publico externo (adoptantes, donantes), NO es personal
 * del refugio. Tabla y login totalmente separados de "usuarios". */
typedef struct {
    int  id;
    char correo[128];
    char nombre[64];
} Cliente;

/* ---------- Ciclo de vida ---------- */'''

ANCLA_DBH_AUTH = '''int  usuario_autenticar(const char *username, const char *password, int *rol_out);'''

NUEVO_DBH_AUTH = '''int  usuario_autenticar(const char *username, const char *password, int *rol_out);

/* ---------- Clientes (publico externo: adoptantes y donantes) ---------- */
int  cliente_registrar(const char *correo, const char *password, const char *nombre);
int  cliente_autenticar(const char *correo, const char *password, Cliente *out);
int  mascota_listar_disponibles(Mascota **out, int *n);'''


# ---------------------------------------------------------------
# 2) db.c
# ---------------------------------------------------------------

ANCLA_DBC_SCHEMA = '''    "CREATE TABLE IF NOT EXISTS usuarios ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  username TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  rol INTEGER NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS notas_veterinario ("'''

NUEVO_DBC_SCHEMA = '''    "CREATE TABLE IF NOT EXISTS usuarios ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  username TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  rol INTEGER NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS clientes ("
    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  correo TEXT NOT NULL UNIQUE,"
    "  password TEXT NOT NULL,"
    "  nombre TEXT NOT NULL"
    ");"
    "CREATE TABLE IF NOT EXISTS notas_veterinario ("'''

ANCLA_DBC_FUNC = '''int usuario_autenticar(const char *username, const char *password, int *rol_out) {
    /* Ya no se compara la contrasena dentro del SQL (WHERE password=?):
     * se trae el hash guardado para ese usuario y se compara aca,
     * usando crypt() (que extrae la sal del propio hash guardado y
     * recalcula, sin necesitar guardarla aparte). */
    const char *sql = "SELECT rol, password FROM usuarios WHERE username=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int rol = sqlite3_column_int(st, 0);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 1);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (rol_out) *rol_out = rol;
                ok = 0;
            }
        }
    }
    sqlite3_finalize(st);
    return ok;
}

/* ---------------- Mascotas ---------------- */'''

NUEVO_DBC_FUNC = '''int usuario_autenticar(const char *username, const char *password, int *rol_out) {
    /* Ya no se compara la contrasena dentro del SQL (WHERE password=?):
     * se trae el hash guardado para ese usuario y se compara aca,
     * usando crypt() (que extrae la sal del propio hash guardado y
     * recalcula, sin necesitar guardarla aparte). */
    const char *sql = "SELECT rol, password FROM usuarios WHERE username=?;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(st, 1, username, -1, SQLITE_STATIC);
    int ok = -1;
    if (sqlite3_step(st) == SQLITE_ROW) {
        int rol = sqlite3_column_int(st, 0);
        const unsigned char *hash_guardado = sqlite3_column_text(st, 1);
        if (hash_guardado) {
            char *resultado = crypt(password, (const char *)hash_guardado);
            if (resultado && strcmp(resultado, (const char *)hash_guardado) == 0) {
                if (rol_out) *rol_out = rol;
                ok = 0;
            }
        }
    }
    sqlite3_finalize(st);
    return ok;
}

/* ---------------- Clientes (publico externo) ---------------- */

int cliente_registrar(const char *correo, const char *password, const char *nombre) {
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
}

int cliente_autenticar(const char *correo, const char *password, Cliente *out) {
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
}

int mascota_listar_disponibles(Mascota **out, int *n) {
    const char *sql =
        "SELECT id,nombre,especie,raza,edad,estado,fecha_ingreso FROM mascotas "
        "WHERE estado='disponible' ORDER BY id;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;

    int cap = 16, cnt = 0;
    Mascota *arr = malloc(sizeof(Mascota) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Mascota) * cap); }
        Mascota *m = &arr[cnt++];
        memset(m, 0, sizeof(*m));
        m->id = sqlite3_column_int(st, 0);
        snprintf(m->nombre, sizeof(m->nombre), "%s", (const char *)sqlite3_column_text(st, 1));
        snprintf(m->especie, sizeof(m->especie), "%s", (const char *)sqlite3_column_text(st, 2));
        const unsigned char *raza = sqlite3_column_text(st, 3);
        snprintf(m->raza, sizeof(m->raza), "%s", raza ? (const char *)raza : "");
        m->edad = sqlite3_column_int(st, 4);
        snprintf(m->estado, sizeof(m->estado), "%s", (const char *)sqlite3_column_text(st, 5));
        snprintf(m->fecha_ingreso, sizeof(m->fecha_ingreso), "%s", (const char *)sqlite3_column_text(st, 6));
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Mascotas ---------------- */'''


# ---------------------------------------------------------------
# 3) main_gtk.c
# ---------------------------------------------------------------

ANCLA_GTK_INSERCION = '''/* Muestra el dialogo de inicio de sesion de PawOS (usuario/contrasena),
 * usando la misma tabla "usuarios" y la misma funcion de autenticacion
 * (usuario_autenticar() en db.c, contrasenas guardadas como hash) que ya
 * usa la version de texto (pantalla_login.c) -- ya NO se usa el usuario
 * de Linux ni sus grupos para decidir el rol. Hasta 3 intentos, igual
 * que la version de texto. Devuelve TRUE y llena usuario_out/rol_out si
 * el login fue correcto, o FALSE si cancelo o agoto los intentos (en
 * ambos casos el programa debe cerrarse sin abrir la ventana principal). */
static gboolean mostrar_login_gtk(char *usuario_out, size_t usuario_len, Rol *rol_out) {'''

NUEVO_GTK_INSERCION = '''/* =================================================================
 * Acceso de Clientes (publico externo: adoptantes y donantes). No es
 * un rol mas dentro de "usuarios" (esos son Administrador, Veterinario
 * y Voluntario, el personal del refugio) -- es una cuenta totalmente
 * aparte, en su propia tabla "clientes" (correo + contrasena), con su
 * propia ventana simplificada: solo ve las mascotas disponibles para
 * adopcion y puede solicitar una adopcion o hacer una donacion. No ve
 * nada de lo interno (procesos, memoria, reportes, vacunas, etc.).
 * ================================================================= */

enum { RESPUESTA_COLABORADOR = 1, RESPUESTA_CLIENTE = 2, RESPUESTA_REGISTRARME = 3 };

typedef enum { ENTRADA_CANCELAR, ENTRADA_COLABORADOR, ENTRADA_CLIENTE } TipoEntrada;

enum {
    COL_MC_ID = 0,
    COL_MC_NOMBRE,
    COL_MC_ESPECIE,
    COL_MC_RAZA,
    COL_MC_EDAD,
    N_COL_MASCOTAS_CLIENTE
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    char          nombre_cliente[64];
} ContextoCliente;

static void cargar_mascotas_disponibles(ContextoCliente *ctx) {
    gtk_list_store_clear(ctx->store);

    Mascota *ms;
    int n;
    if (mascota_listar_disponibles(&ms, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de mascotas.", TRUE);
        return;
    }
    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_MC_ID, ms[i].id,
            COL_MC_NOMBRE, ms[i].nombre,
            COL_MC_ESPECIE, ms[i].especie,
            COL_MC_RAZA, ms[i].raza,
            COL_MC_EDAD, ms[i].edad,
            -1);
    }
    free(ms);
}

static void on_refrescar_mascotas_cliente_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    cargar_mascotas_disponibles((ContextoCliente *)datos);
}

static void on_solicitar_adopcion_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoCliente *ctx = (ContextoCliente *)datos;

    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(ctx->treeview));
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una mascota de la lista.", TRUE);
        return;
    }

    int id_mascota;
    gchar *nombre_mascota = NULL;
    gtk_tree_model_get(modelo, &iter, COL_MC_ID, &id_mascota, COL_MC_NOMBRE, &nombre_mascota, -1);

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Solicitar adopcion", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Enviar solicitud", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    gchar *texto_mascota = g_strdup_printf("Mascota: %s", nombre_mascota);
    GtkWidget *lbl_mascota = gtk_label_new(texto_mascota);
    g_free(texto_mascota);
    gtk_widget_set_halign(lbl_mascota, GTK_ALIGN_START);

    GtkWidget *e_contacto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_contacto), "Telefono o correo de contacto");

    gtk_grid_attach(GTK_GRID(cuadricula), lbl_mascota, 0, 0, 2, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Tu contacto:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_contacto, 1, 1, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Adopcion a;
        memset(&a, 0, sizeof(a));
        a.mascota_id = id_mascota;
        snprintf(a.adoptante_nombre, sizeof(a.adoptante_nombre), "%s", ctx->nombre_cliente);
        snprintf(a.adoptante_contacto, sizeof(a.adoptante_contacto), "%s", gtk_entry_get_text(GTK_ENTRY(e_contacto)));
        hoy(a.fecha_adopcion, sizeof(a.fecha_adopcion));

        if (adopcion_registrar(&a) == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "Solicitud de adopcion enviada. El refugio se pondra en contacto contigo.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo enviar la solicitud.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
    g_free(nombre_mascota);
}

static void on_hacer_donacion_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoCliente *ctx = (ContextoCliente *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Hacer una donacion", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Donar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_contacto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_contacto), "Telefono o correo de contacto");
    GtkWidget *e_monto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_monto), "0.00");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Tu contacto:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_contacto, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Monto a donar:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_monto, 1, 1, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Donante d;
        memset(&d, 0, sizeof(d));
        snprintf(d.nombre, sizeof(d.nombre), "%s", ctx->nombre_cliente);
        snprintf(d.contacto, sizeof(d.contacto), "%s", gtk_entry_get_text(GTK_ENTRY(e_contacto)));
        d.monto = atof(gtk_entry_get_text(GTK_ENTRY(e_monto)));
        hoy(d.fecha, sizeof(d.fecha));

        if (donante_agregar(&d) == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Gracias por tu donacion.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo registrar la donacion.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void construir_ventana_cliente(const char *nombre_cliente) {
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
    GtkWidget *btn_salir     = gtk_button_new_with_label("Salir");

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
}

/* Formulario para crear una cuenta de Cliente nueva (correo, nombre,
 * contrasena), llamado desde el boton "Registrarme" del login de
 * clientes. Devuelve TRUE y llena nombre_out si se creo la cuenta. */
static gboolean mostrar_registro_cliente(char *nombre_out, size_t nombre_len) {
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
}

/* Login de Clientes (correo/contrasena, tabla "clientes"). Si todavia
 * no tiene cuenta, el boton "Registrarme" la crea ahi mismo. Hasta 3
 * intentos fallidos (crear cuenta no cuenta como intento). Devuelve
 * TRUE y llena nombre_out si el login (o el registro) fue exitoso. */
static gboolean mostrar_login_cliente(char *nombre_out, size_t nombre_len) {
    int intentos = 0;
    const int max_intentos = 3;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,
            "Cancelar", GTK_RESPONSE_CANCEL,
            "Registrarme", RESPUESTA_REGISTRARME,
            "Ingresar", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area_contenido), caja);

        GtkWidget *titulo = gtk_label_new(NULL);
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\\xF0\\x9F\\x90\\xBE Acceso de Clientes</span>");
        gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

        GtkWidget *grid = gtk_grid_new();
        gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
        gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
        gtk_box_pack_start(GTK_BOX(caja), grid, FALSE, FALSE, 0);

        GtkWidget *lbl_correo = gtk_label_new("Correo:");
        gtk_widget_set_halign(lbl_correo, GTK_ALIGN_END);
        GtkWidget *entrada_correo = gtk_entry_new();
        gtk_grid_attach(GTK_GRID(grid), lbl_correo, 0, 0, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_correo, 1, 0, 1, 1);

        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_correo), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);
        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_ACCEPT);

        if (intentos > 0) {
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

        if (respuesta == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            char nombre_nuevo[64] = "";
            if (mostrar_registro_cliente(nombre_nuevo, sizeof(nombre_nuevo))) {
                snprintf(nombre_out, nombre_len, "%s", nombre_nuevo);
                mostrar_mensaje(NULL, "Cuenta creada. Bienvenido a PawOS.", FALSE);
                return TRUE;
            }
            continue;
        }

        if (respuesta != GTK_RESPONSE_ACCEPT) {
            gtk_widget_destroy(dialogo);
            return FALSE;
        }

        const char *correo_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_correo));
        const char *password_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_password));

        Cliente c;
        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, &c) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            snprintf(nombre_out, nombre_len, "%s", c.nombre);
            return TRUE;
        }
        intentos++;
    }

    GtkWidget *aviso = gtk_message_dialog_new(
        NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR, GTK_BUTTONS_OK,
        "Demasiados intentos fallidos.");
    gtk_dialog_run(GTK_DIALOG(aviso));
    gtk_widget_destroy(aviso);
    return FALSE;
}

/* Primera pantalla al abrir PawOS Refugio: elegir si quien entra es
 * personal del refugio (Colaborador, login existente contra la tabla
 * "usuarios") o publico externo (Cliente, tabla "clientes" aparte). */
static TipoEntrada mostrar_selector_entrada(void) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS Refugio", NULL, GTK_DIALOG_MODAL,
        "Salir", GTK_RESPONSE_CANCEL,
        "Soy Colaborador", RESPUESTA_COLABORADOR,
        "Soy Cliente", RESPUESTA_CLIENTE,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 16);
    gtk_container_add(GTK_CONTAINER(area), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo),
        "<span size='large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new("\\xC2\\xBF" "Como quieres entrar?");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    gtk_widget_show_all(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == RESPUESTA_COLABORADOR) return ENTRADA_COLABORADOR;
    if (respuesta == RESPUESTA_CLIENTE) return ENTRADA_CLIENTE;
    return ENTRADA_CANCELAR;
}

/* Muestra el dialogo de inicio de sesion de PawOS (usuario/contrasena),
 * usando la misma tabla "usuarios" y la misma funcion de autenticacion
 * (usuario_autenticar() en db.c, contrasenas guardadas como hash) que ya
 * usa la version de texto (pantalla_login.c) -- ya NO se usa el usuario
 * de Linux ni sus grupos para decidir el rol. Hasta 3 intentos, igual
 * que la version de texto. Devuelve TRUE y llena usuario_out/rol_out si
 * el login fue correcto, o FALSE si cancelo o agoto los intentos (en
 * ambos casos el programa debe cerrarse sin abrir la ventana principal). */
static gboolean mostrar_login_gtk(char *usuario_out, size_t usuario_len, Rol *rol_out) {'''

ANCLA_GTK_MAIN = '''    char usuario[32] = "";
    Rol rol;
    if (!mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
        db_close();
        return 0;
    }

    construir_ventana_principal(rol, usuario);
    gtk_main();

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto, %s.\\n", usuario);
    return 0;
}'''

NUEVO_GTK_MAIN = '''    TipoEntrada entrada = mostrar_selector_entrada();
    if (entrada == ENTRADA_CANCELAR) {
        db_close();
        return 0;
    }

    char nombre_sesion[64] = "";

    if (entrada == ENTRADA_COLABORADOR) {
        char usuario[32] = "";
        Rol rol;
        if (!mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
            db_close();
            return 0;
        }
        snprintf(nombre_sesion, sizeof(nombre_sesion), "%s", usuario);
        construir_ventana_principal(rol, usuario);
    } else {
        if (!mostrar_login_cliente(nombre_sesion, sizeof(nombre_sesion))) {
            db_close();
            return 0;
        }
        construir_ventana_cliente(nombre_sesion);
    }

    gtk_main();

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto, %s.\\n", nombre_sesion);
    return 0;
}'''


def aplicar(ruta, pares, nombre_archivo):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, nuevo in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta} no se encontro (o se encontro mas de una vez) el bloque esperado.")
            print("       Puede que agregar-login-gui.py todavia no se haya aplicado,")
            print("       o que el archivo ya haya sido modificado. No se cambio nada.")
            sys.exit(1)
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ruta, ruta + ".bak4")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{nombre_archivo}: OK (backup en {ruta}.bak4)")


def main():
    aplicar(ARCHIVO_DB_H, [
        (ANCLA_DBH_STRUCT, NUEVO_DBH_STRUCT),
        (ANCLA_DBH_AUTH, NUEVO_DBH_AUTH),
    ], "src/db/db.h")

    aplicar(ARCHIVO_DB_C, [
        (ANCLA_DBC_SCHEMA, NUEVO_DBC_SCHEMA),
        (ANCLA_DBC_FUNC, NUEVO_DBC_FUNC),
    ], "src/db/db.c")

    aplicar(ARCHIVO_GTK, [
        (ANCLA_GTK_INSERCION, NUEVO_GTK_INSERCION),
        (ANCLA_GTK_MAIN, NUEVO_GTK_MAIN),
    ], "src/main_gtk.c")

    print("")
    print("Listo. Ahora corre:  make clean-gui && make gui")
    print("")
    print("Al abrir el programa aparecen 2 botones: 'Soy Colaborador' (login de")
    print("siempre) y 'Soy Cliente' (correo/contrasena, tabla nueva 'clientes';")
    print("si es la primera vez, el boton 'Registrarme' crea la cuenta ahi mismo).")


if __name__ == "__main__":
    main()
