/*
 * main_gtk.c - Interfaz grafica (GTK3) de PawOS Refugio.
 *
 * Este archivo REEMPLAZA la interfaz de texto (ncurses) por una interfaz
 * grafica amigable, pero reutiliza tal cual la capa de datos existente:
 *   - db.c / db.h         -> mascotas, vacunas, adopciones, donantes, reportes
 *   - auth.c / auth.h     -> usuario y rol segun los grupos de Linux
 *   - procesos.c / procesos.h -> administracion de procesos
 *   - memoria.c / memoria.h   -> administracion de memoria (paginacion)
 *
 * No se modifico ni una linea de esos archivos: el programa CLI
 * (pawos-refugio, basado en main.c + pantallas.c + ui.c) sigue
 * compilando y funcionando exactamente igual que antes. Este es un
 * binario nuevo (pawos-refugio-gui) que se agrega al lado, pensado
 * para poder comparar CLI vs GUI sobre la misma base de datos.
 *
 * Los 7 modulos del menu principal estan implementados, respetando
 * exactamente las mismas restricciones de rol que ya existian en
 * pantallas.c / pantalla_procesos.c / pantalla_memoria.c:
 *   - Mascotas:    todos los roles ven y registran; solo Admin y
 *                  Veterinario cambian estado o eliminan.
 *   - Vacunas:     todos los roles ven; solo Admin y Veterinario registran.
 *   - Adopciones:  todos los roles ven y registran.
 *   - Donantes:    bloqueado por completo para Voluntario.
 *   - Reportes:    bloqueado por completo para Voluntario.
 *   - Procesos:    solo Administrador.
 *   - Memoria:     solo Administrador.
 */

#include <gtk/gtk.h>
#include <cairo-pdf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <errno.h>
#include "db/db.h"
#include "auth/auth.h"
#include "procesos/procesos.h"
#include "memoria/memoria.h"
#include "../include/version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define ID_PROCESO_DEMO 1u

/* ---------------------------------------------------------------
 * Utilidades comunes
 * --------------------------------------------------------------- */

static void hoy(char *buf, int len) {
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(buf, len, "%Y-%m-%d", &tmv);
}

static void mostrar_mensaje(GtkWindow *padre, const char *msg, gboolean es_error) {
    GtkWidget *dialogo = gtk_message_dialog_new(
        padre, GTK_DIALOG_MODAL,
        es_error ? GTK_MESSAGE_ERROR : GTK_MESSAGE_INFO,
        GTK_BUTTONS_OK, "%s", msg);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

/* Dialogo generico para pedir un numero entero (equivalente a
 * ui_pedir_entero() de la version CLI). Devuelve FALSE si el usuario
 * cancelo. */
static gboolean pedir_entero_dialog(GtkWindow *padre, const char *titulo, const char *etiqueta, int *out) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        titulo, padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Aceptar", GTK_RESPONSE_OK, NULL);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    GtkWidget *etiqueta_w = gtk_label_new(etiqueta);
    gtk_widget_set_halign(etiqueta_w, GTK_ALIGN_START);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(entrada), GTK_INPUT_PURPOSE_DIGITS);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);

    gtk_box_pack_start(GTK_BOX(caja), etiqueta_w, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), entrada, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);

    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    gboolean ok = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        *out = atoi(gtk_entry_get_text(GTK_ENTRY(entrada)));
        ok = TRUE;
    }
    gtk_widget_destroy(dialogo);
    return ok;
}

/* Ventana emergente con la lista completa de mascotas (ID, nombre,
 * especie, estado) para elegir una sin tener que memorizar/adivinar el
 * ID. Devuelve TRUE y llena id_out si se selecciona una fila y se
 * confirma; FALSE si se cancela. */
static gboolean seleccionar_mascota_dialog(GtkWindow *padre, int *id_out) {
    enum { COL_SM_ID = 0, COL_SM_NOMBRE, COL_SM_ESPECIE, COL_SM_ESTADO, N_COL_SM };

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Buscar mascota", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Seleccionar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 420, 320);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 10);

    GtkListStore *store = gtk_list_store_new(N_COL_SM,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);

    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar(&ms, &n) == 0) {
        for (int i = 0; i < n; i++) {
            GtkTreeIter iter;
            gtk_list_store_append(store, &iter);
            gtk_list_store_set(store, &iter,
                COL_SM_ID, ms[i].id,
                COL_SM_NOMBRE, ms[i].nombre,
                COL_SM_ESPECIE, ms[i].especie,
                COL_SM_ESTADO, ms[i].estado,
                -1);
        }
        free(ms);
    }

    GtkWidget *treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    g_object_unref(store);

    GtkCellRenderer *r;
    r = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview), -1, "ID", r, "text", COL_SM_ID, NULL);
    r = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview), -1, "Nombre", r, "text", COL_SM_NOMBRE, NULL);
    r = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview), -1, "Especie", r, "text", COL_SM_ESPECIE, NULL);
    r = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview), -1, "Estado", r, "text", COL_SM_ESTADO, NULL);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), treeview);
    gtk_box_pack_start(GTK_BOX(area), scroll, TRUE, TRUE, 0);

    gtk_widget_show_all(dialogo);

    gboolean ok = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(treeview));
        GtkTreeModel *modelo;
        GtkTreeIter iter;
        if (gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
            gtk_tree_model_get(modelo, &iter, COL_SM_ID, id_out, -1);
            ok = TRUE;
        }
    }
    gtk_widget_destroy(dialogo);
    return ok;
}

static void on_buscar_mascota_id_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWidget *entrada = GTK_WIDGET(datos);
    GtkWidget *toplevel = gtk_widget_get_toplevel(entrada);
    if (!GTK_IS_WINDOW(toplevel)) return;

    int id;
    if (seleccionar_mascota_dialog(GTK_WINDOW(toplevel), &id)) {
        char buf[16];
        snprintf(buf, sizeof(buf), "%d", id);
        gtk_entry_set_text(GTK_ENTRY(entrada), buf);
    }
}

/* Igual que pedir_entero_dialog(), pero pensado para elegir el ID de
 * una mascota: junto al campo de texto (por si ya se sabe el ID de
 * memoria) hay un boton "Buscar mascota..." que abre la lista completa
 * (seleccionar_mascota_dialog) para elegirla sin tener que adivinar el
 * numero. Se usa en "Registrar vacuna" y "Registrar adopcion". */
static gboolean pedir_mascota_id_dialog(GtkWindow *padre, const char *titulo, const char *etiqueta, int *out) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        titulo, padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Aceptar", GTK_RESPONSE_OK, NULL);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    GtkWidget *etiqueta_w = gtk_label_new(etiqueta);
    gtk_widget_set_halign(etiqueta_w, GTK_ALIGN_START);

    GtkWidget *fila = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(entrada), GTK_INPUT_PURPOSE_DIGITS);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_widget_set_hexpand(entrada, TRUE);
    GtkWidget *btn_buscar = gtk_button_new_with_label("Buscar mascota...");
    g_signal_connect(btn_buscar, "clicked", G_CALLBACK(on_buscar_mascota_id_clicked), entrada);

    gtk_box_pack_start(GTK_BOX(fila), entrada, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(fila), btn_buscar, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja), etiqueta_w, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), fila, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);

    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    gboolean ok = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const char *texto = gtk_entry_get_text(GTK_ENTRY(entrada));
        if (texto && texto[0] != '\0') {
            *out = atoi(texto);
            ok = TRUE;
        }
    }
    gtk_widget_destroy(dialogo);
    return ok;
}

/* Libera un bloque de contexto asignado con g_malloc/g_malloc0 cuando
 * su ventana se destruye. Se reutiliza para todos los modulos nuevos. */
static void liberar_contexto(GtkWidget *widget, gpointer datos) {
    (void)widget;
    g_free(datos);
}

/* Proveedor de CSS actual, para poder reemplazarlo si el usuario cambia
 * el tema claro/oscuro del sistema mientras la app esta abierta. */
static GtkCssProvider *g_proveedor_estilos = NULL;

/* Detecta si el escritorio esta en modo oscuro, sin ningun interruptor
 * propio: se apoya en la preferencia que ya expone GTK/el escritorio
 * (GNOME, XFCE, etc. la sincronizan via GtkSettings). Como respaldo,
 * tambien revisa si el nombre del tema activo contiene "dark". */
static gboolean modo_oscuro_activo(void) {
    GtkSettings *settings = gtk_settings_get_default();
    if (!settings) return FALSE;

    gboolean prefiere_oscuro = FALSE;
    g_object_get(settings, "gtk-application-prefer-dark-theme", &prefiere_oscuro, NULL);
    if (prefiere_oscuro) return TRUE;

    gchar *nombre_tema = NULL;
    g_object_get(settings, "gtk-theme-name", &nombre_tema, NULL);
    gboolean tema_oscuro = (nombre_tema != NULL && strstr(nombre_tema, "dark") != NULL);
    g_free(nombre_tema);
    return tema_oscuro;
}

/* Estilos con la paleta de PawOS (verde bosque), con variante clara y
 * oscura segun la preferencia del sistema -- automatico, sin boton ni
 * interruptor en la propia app. */
static void aplicar_estilos(void) {
    gboolean oscuro = modo_oscuro_activo();

    const char *fondo_ventana    = oscuro ? "#1B211C" : "#EDF2EA";
    const char *color_texto      = oscuro ? "#E7ECE4" : "#1C2620";
    const char *fondo_dialogo    = oscuro ? "#232B24" : "#F7FAF6";
    const char *fondo_tabla      = oscuro ? "#20271F" : "#FFFFFF";
    const char *texto_tabla      = oscuro ? "#E7ECE4" : "#1C2620";
    const char *seleccion_bg     = oscuro ? "#2E6B3F" : "#BFE6C9";
    const char *seleccion_fg     = oscuro ? "#F2F8F0" : "#103018";
    const char *deshabilitado_bg = oscuro ? "#3A423B" : "#CBD3C7";
    const char *deshabilitado_fg = oscuro ? "#8B948B" : "#7C877A";

    gchar *css = g_strdup_printf(
        /* Fondo general de la app */
        "window { background-color: %s; }"
        "label { color: %s; }"

        /* Banner de encabezado (ventana principal): degradado verde bosque,
         * igual en ambos modos porque es un color de marca, no de fondo. */
        ".encabezado-banner {"
        "  background-image: linear-gradient(135deg, #23924B 0%%, #12451F 100%%);"
        "  border-radius: 16px;"
        "  padding: 18px;"
        "}"
        ".encabezado-banner label { color: #FFFFFF; }"
        ".subtitulo-banner { color: #D9F2E0; }"

        /* Insignia (pill) de rol */
        ".badge {"
        "  border-radius: 999px;"
        "  padding: 3px 14px;"
        "  font-weight: bold;"
        "}"
        ".badge-admin       { background-color: #E8B23D; color: #3B2A05; }"
        ".badge-veterinario { background-color: #2C8C99; color: #FFFFFF; }"
        ".badge-voluntario  { background-color: #6C7A76; color: #FFFFFF; }"
        ".badge-rescatista    { background-color: #C1440E; color: #FFFFFF; }"
        ".badge-recepcionista { background-color: #7A4FA3; color: #FFFFFF; }"

        /* Botones generales */
        "button {"
        "  padding: 10px;"
        "  border-radius: 10px;"
        "  transition: 150ms ease-in-out;"
        "}"
        "button.modulo {"
        "  color: #FFFFFF;"
        "  font-weight: bold;"
        "  border: none;"
        "  box-shadow: 0 2px 5px rgba(0,0,0,0.28);"
        "}"
        "button.modulo:hover  { box-shadow: 0 4px 9px rgba(0,0,0,0.32); }"
        "button.modulo:active { box-shadow: 0 1px 2px rgba(0,0,0,0.3) inset; }"

        /* Categorias de modulo, coloreadas por tipo de tarea (mismo color
         * en ambos modos: son colores de acento, ya tienen buen contraste). */
        "button.cat-refugio        { background-color: #23924B; }"
        "button.cat-refugio:hover  { background-color: #1B7A3D; }"
        "button.cat-gestion        { background-color: #2C6E8F; }"
        "button.cat-gestion:hover  { background-color: #215577; }"
        "button.cat-sistema        { background-color: #6B4F9E; }"
        "button.cat-sistema:hover  { background-color: #543C7D; }"

        "button.modulo:disabled {"
        "  background-color: %s; color: %s; box-shadow: none;"
        "}"
        "button:disabled { opacity: 0.75; }"

        "button.salir { background-color: #C0342C; color: #FFFFFF; font-weight: bold; border: none; }"
        "button.salir:hover { background-color: #99271F; }"

        /* Tablas: encabezado con color de marca (fijo) y fondo/texto de
         * filas que si cambian segun el modo claro/oscuro. */
        "treeview, treeview.view { background-color: %s; color: %s; }"
        "treeview header button {"
        "  background-color: #23924B; color: #FFFFFF; font-weight: bold; padding: 7px;"
        "}"
        "treeview:selected, treeview.view:selected { background-color: %s; color: %s; }"

        /* Dialogos y campos de texto */
        "dialog { background-color: %s; }"
        "entry, textview, textview text { background-color: %s; color: %s; }",
        fondo_ventana, color_texto,
        deshabilitado_bg, deshabilitado_fg,
        fondo_tabla, texto_tabla,
        seleccion_bg, seleccion_fg,
        fondo_dialogo,
        fondo_dialogo, color_texto);

    if (g_proveedor_estilos) {
        gtk_style_context_remove_provider_for_screen(
            gdk_screen_get_default(), GTK_STYLE_PROVIDER(g_proveedor_estilos));
        g_object_unref(g_proveedor_estilos);
        g_proveedor_estilos = NULL;
    }

    g_proveedor_estilos = gtk_css_provider_new();
    gtk_css_provider_load_from_data(g_proveedor_estilos, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(),
        GTK_STYLE_PROVIDER(g_proveedor_estilos),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_free(css);
}

/* Si el usuario cambia el tema claro/oscuro del sistema mientras PawOS
 * esta abierto, esto vuelve a generar los estilos automaticamente --
 * sigue sin haber ningun interruptor dentro de la propia app. */
static void on_cambio_tema_sistema(GObject *obj, GParamSpec *pspec, gpointer datos) {
    (void)obj;
    (void)pspec;
    (void)datos;
    aplicar_estilos();
}

/* =================================================================
 * Modulo: Gestion de Mascotas
 * ================================================================= */

enum {
    COL_M_ID = 0,
    COL_M_NOMBRE,
    COL_M_ESPECIE,
    COL_M_RAZA,
    COL_M_EDAD,
    COL_M_ESTADO,
    COL_M_FECHA,
    N_COL_MASCOTAS
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    Rol           rol;
} ContextoMascotas;

static void cargar_mascotas(ContextoMascotas *ctx) {
    gtk_list_store_clear(ctx->store);

    Mascota *ms;
    int n;
    if (mascota_listar(&ms, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de mascotas.", TRUE);
        return;
    }

    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_M_ID, ms[i].id,
            COL_M_NOMBRE, ms[i].nombre,
            COL_M_ESPECIE, ms[i].especie,
            COL_M_RAZA, ms[i].raza,
            COL_M_EDAD, ms[i].edad,
            COL_M_ESTADO, ms[i].estado,
            COL_M_FECHA, ms[i].fecha_ingreso,
            -1);
    }
    free(ms);
}

static gboolean obtener_id_seleccionado(GtkWidget *treeview, int columna_id, int *id_out) {
    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(treeview));
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(sel, &modelo, &iter)) return FALSE;
    gtk_tree_model_get(modelo, &iter, columna_id, id_out, -1);
    return TRUE;
}

static void on_registrar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrar nueva mascota", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_nombre  = gtk_entry_new();
    GtkWidget *e_especie = gtk_entry_new();
    GtkWidget *e_raza    = gtk_entry_new();
    GtkWidget *e_edad    = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_especie), "perro / gato / otro");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_raza), "opcional");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Especie:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_especie, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Raza:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_raza, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Edad (anios):"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_edad, 1, 3, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Mascota m;
        memset(&m, 0, sizeof(m));
        snprintf(m.nombre, sizeof(m.nombre), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(m.especie, sizeof(m.especie), "%s", gtk_entry_get_text(GTK_ENTRY(e_especie)));
        snprintf(m.raza, sizeof(m.raza), "%s", gtk_entry_get_text(GTK_ENTRY(e_raza)));
        m.edad = atoi(gtk_entry_get_text(GTK_ENTRY(e_edad)));
        strcpy(m.estado, "disponible");
        hoy(m.fecha_ingreso, sizeof(m.fecha_ingreso));

        if (strlen(m.nombre) == 0 || strlen(m.especie) == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "El nombre y la especie son obligatorios.", TRUE);
        } else if (mascota_agregar(&m) == 0) {
            cargar_mascotas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Mascota registrada correctamente.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la mascota.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void on_cambiar_estado_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    int id;
    if (!obtener_id_seleccionado(ctx->treeview, COL_M_ID, &id)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una mascota de la lista.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Cambiar estado", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Aplicar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));

    GtkWidget *combo = gtk_combo_box_text_new();
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "disponible");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "en_proceso");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "adoptado");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), "tratamiento");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
    gtk_container_set_border_width(GTK_CONTAINER(combo), 12);
    gtk_container_add(GTK_CONTAINER(area), combo);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        gchar *nuevo = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(combo));
        if (nuevo != NULL && mascota_actualizar_estado(id, nuevo) == 0) {
            cargar_mascotas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Estado actualizado.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar el estado.", TRUE);
        }
        g_free(nuevo);
    }
    gtk_widget_destroy(dialogo);
}

static void on_eliminar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    int id;
    if (!obtener_id_seleccionado(ctx->treeview, COL_M_ID, &id)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una mascota de la lista.", TRUE);
        return;
    }

    GtkWidget *confirmar = gtk_message_dialog_new(
        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_YES_NO,
        "Esta seguro que desea eliminar la mascota con ID %d?\nEsta accion no se puede deshacer.", id);
    int respuesta = gtk_dialog_run(GTK_DIALOG(confirmar));
    gtk_widget_destroy(confirmar);

    if (respuesta == GTK_RESPONSE_YES) {
        if (mascota_eliminar(id) == 0) {
            cargar_mascotas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Mascota eliminada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo eliminar la mascota.", TRUE);
        }
    }
}

static void on_refrescar_mascotas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    cargar_mascotas((ContextoMascotas *)datos);
}

static void abrir_pantalla_mascotas(GtkWidget *padre, Rol rol) {
    ContextoMascotas *ctx = g_malloc0(sizeof(ContextoMascotas));
    ctx->rol = rol;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Gestion de Mascotas");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 760, 480);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Gestion de Mascotas</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_MASCOTAS,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_MASCOTAS] = {"ID", "Nombre", "Especie", "Raza", "Edad", "Estado", "Ingreso"};
    for (int i = 0; i < N_COL_MASCOTAS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar nueva");
    GtkWidget *btn_estado    = gtk_button_new_with_label("Cambiar estado");
    GtkWidget *btn_eliminar  = gtk_button_new_with_label("Eliminar");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_eliminar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que en pantallas.c (CLI): el voluntario solo ve y registra,
     * no cambia estado ni elimina. El boton se muestra siempre, pero
     * queda deshabilitado (no oculto) para que se note que la opcion
     * existe aunque el rol actual no pueda usarla. */
    if (rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(btn_estado, FALSE);
        gtk_widget_set_sensitive(btn_eliminar, FALSE);
        gtk_widget_set_tooltip_text(btn_estado, "Requiere rol Admin o Veterinario.");
        gtk_widget_set_tooltip_text(btn_eliminar, "Requiere rol Admin o Veterinario.");
    }

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_mascotas_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_clicked), ctx);
    g_signal_connect(btn_estado, "clicked", G_CALLBACK(on_cambiar_estado_clicked), ctx);
    g_signal_connect(btn_eliminar, "clicked", G_CALLBACK(on_eliminar_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_mascotas(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Agenda de Vacunas
 * ================================================================= */

enum {
    COL_V_ID = 0,
    COL_V_MASCOTA_ID,
    COL_V_NOMBRE,
    COL_V_APLICACION,
    COL_V_PROXIMA,
    COL_V_OBSERVACIONES,
    N_COL_VACUNAS
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    Rol           rol;
    gboolean      solo_pendientes;
} ContextoVacunas;

static void cargar_vacunas(ContextoVacunas *ctx) {
    gtk_list_store_clear(ctx->store);

    Vacuna *vs;
    int n;
    int rc = ctx->solo_pendientes ? vacuna_pendientes(&vs, &n) : vacuna_listar(&vs, &n);
    if (rc != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de vacunas.", TRUE);
        return;
    }

    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_V_ID, vs[i].id,
            COL_V_MASCOTA_ID, vs[i].mascota_id,
            COL_V_NOMBRE, vs[i].nombre_vacuna,
            COL_V_APLICACION, vs[i].fecha_aplicacion,
            COL_V_PROXIMA, vs[i].fecha_proxima,
            COL_V_OBSERVACIONES, vs[i].observaciones,
            -1);
    }
    free(vs);
}

static void on_ver_todas_vacunas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoVacunas *ctx = (ContextoVacunas *)datos;
    ctx->solo_pendientes = FALSE;
    cargar_vacunas(ctx);
}

static void on_ver_pendientes_vacunas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoVacunas *ctx = (ContextoVacunas *)datos;
    ctx->solo_pendientes = TRUE;
    cargar_vacunas(ctx);
}

static void on_registrar_vacuna_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoVacunas *ctx = (ContextoVacunas *)datos;

    int mascota_id;
    if (!pedir_mascota_id_dialog(GTK_WINDOW(ctx->ventana), "Registrar vacuna", "ID de la mascota:", &mascota_id))
        return;

    Mascota m;
    if (mascota_buscar_por_id(mascota_id, &m) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No existe una mascota con ese ID.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Datos de la vacuna", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_aplic  = gtk_entry_new();
    GtkWidget *e_prox   = gtk_entry_new();
    GtkWidget *e_obs    = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_aplic), "AAAA-MM-DD");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_prox), "AAAA-MM-DD (opcional)");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_obs), "Opcional");

    GtkWidget *e_cliente = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_cliente), "0", "(Ninguno)");
    Cliente *lista_clientes_vac = NULL;
    int n_clientes_vac = 0;
    cliente_listar(&lista_clientes_vac, &n_clientes_vac);
    for (int i = 0; i < n_clientes_vac; i++) {
        char id_cliente_txt[16];
        snprintf(id_cliente_txt, sizeof(id_cliente_txt), "%d", lista_clientes_vac[i].id);
        gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_cliente), id_cliente_txt, lista_clientes_vac[i].nombre);
    }
    gtk_combo_box_set_active(GTK_COMBO_BOX(e_cliente), 0);

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre de la vacuna:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Fecha de aplicacion:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_aplic, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Proxima dosis:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_prox, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Observaciones:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_obs, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Cliente a notificar (opcional):"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_cliente, 1, 4, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));
        const gchar *cliente_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_cliente));
        v.cliente_id = cliente_id_texto ? atoi(cliente_id_texto) : 0;

        if (vacuna_agregar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna registrada.", FALSE);

            /* Si se eligio un Cliente para notificar, se ofrece mandar
             * el recordatorio (PDF por correo y WhatsApp) ya mismo. Si
             * no se eligio ninguno (v.cliente_id == 0), nada de esto
             * corre -- se comporta exactamente igual que antes. */
            if (v.cliente_id > 0) {
                Cliente *cliente_elegido = NULL;
                for (int i = 0; i < n_clientes_vac; i++) {
                    if (lista_clientes_vac[i].id == v.cliente_id) {
                        cliente_elegido = &lista_clientes_vac[i];
                        break;
                    }
                }
                if (cliente_elegido) {
                    gchar *pregunta = g_strdup_printf(
                        "Enviar recordatorio de esta cita a %s por correo y WhatsApp?",
                        cliente_elegido->nombre);
                    GtkWidget *confirmar = gtk_message_dialog_new(
                        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
                        GTK_BUTTONS_YES_NO, "%s", pregunta);
                    g_free(pregunta);
                    gint respuesta = gtk_dialog_run(GTK_DIALOG(confirmar));
                    gtk_widget_destroy(confirmar);
                    if (respuesta == GTK_RESPONSE_YES) {
                        gchar *argv_envio[] = {
                            "x-terminal-emulator", "-e", "pawos-notificar-cita",
                            cliente_elegido->correo, cliente_elegido->telefono,
                            cliente_elegido->nombre, m.nombre, v.nombre_vacuna, v.fecha_proxima,
                            NULL
                        };
                        GError *error_envio = NULL;
                        if (!g_spawn_async(NULL, argv_envio, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, &error_envio)) {
                            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo abrir el envio de recordatorio.", TRUE);
                            if (error_envio) g_error_free(error_envio);
                        }
                    }
                }
            }
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la vacuna.", TRUE);
        }
    }
    free(lista_clientes_vac);
    gtk_widget_destroy(dialogo);
}

static void abrir_pantalla_vacunas(GtkWidget *padre, Rol rol) {
    ContextoVacunas *ctx = g_malloc0(sizeof(ContextoVacunas));
    ctx->rol = rol;
    ctx->solo_pendientes = FALSE;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Agenda de Vacunas");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 720, 460);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Agenda de Vacunas</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_VACUNAS,
        G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_VACUNAS] = {"ID", "ID Mascota", "Vacuna", "Aplicada", "Proxima", "Observaciones"};
    for (int i = 0; i < N_COL_VACUNAS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_todas       = gtk_button_new_with_label("Ver todas");
    GtkWidget *btn_pendientes  = gtk_button_new_with_label("Ver pendientes/vencidas");
    GtkWidget *btn_registrar   = gtk_button_new_with_label("Registrar vacuna");
    GtkWidget *btn_cerrar      = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_todas, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_pendientes, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que en pantallas.c: solo Admin y Veterinario registran vacunas.
     * Se muestra el boton siempre, solo se deshabilita para Voluntario. */
    if (rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(btn_registrar, FALSE);
        gtk_widget_set_tooltip_text(btn_registrar, "Requiere rol Admin o Veterinario.");
    }

    g_signal_connect(btn_todas, "clicked", G_CALLBACK(on_ver_todas_vacunas_clicked), ctx);
    g_signal_connect(btn_pendientes, "clicked", G_CALLBACK(on_ver_pendientes_vacunas_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_vacuna_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_vacunas(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Control de Adopciones
 * ================================================================= */

enum {
    COL_A_ID = 0,
    COL_A_MASCOTA_ID,
    COL_A_ADOPTANTE,
    COL_A_CONTACTO,
    COL_A_FECHA,
    N_COL_ADOPCIONES
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    Rol           rol;
} ContextoAdopciones;

static void cargar_adopciones(ContextoAdopciones *ctx) {
    gtk_list_store_clear(ctx->store);

    Adopcion *ad;
    int n;
    if (adopcion_listar(&ad, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de adopciones.", TRUE);
        return;
    }

    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_A_ID, ad[i].id,
            COL_A_MASCOTA_ID, ad[i].mascota_id,
            COL_A_ADOPTANTE, ad[i].adoptante_nombre,
            COL_A_CONTACTO, ad[i].adoptante_contacto,
            COL_A_FECHA, ad[i].fecha_adopcion,
            -1);
    }
    free(ad);
}

static void on_refrescar_adopciones_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    cargar_adopciones((ContextoAdopciones *)datos);
}

static void on_registrar_adopcion_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAdopciones *ctx = (ContextoAdopciones *)datos;

    int mascota_id;
    if (!pedir_mascota_id_dialog(GTK_WINDOW(ctx->ventana), "Registrar adopcion", "ID de la mascota a adoptar:", &mascota_id))
        return;

    Mascota m;
    if (mascota_buscar_por_id(mascota_id, &m) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No existe una mascota con ese ID.", TRUE);
        return;
    }
    if (strcmp(m.estado, "adoptado") == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Esa mascota ya fue adoptada.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Datos del adoptante", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_nombre   = gtk_entry_new();
    GtkWidget *e_contacto = gtk_entry_new();
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre del adoptante:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Contacto:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_contacto, 1, 1, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Adopcion a;
        memset(&a, 0, sizeof(a));
        a.mascota_id = mascota_id;
        snprintf(a.adoptante_nombre, sizeof(a.adoptante_nombre), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(a.adoptante_contacto, sizeof(a.adoptante_contacto), "%s", gtk_entry_get_text(GTK_ENTRY(e_contacto)));
        hoy(a.fecha_adopcion, sizeof(a.fecha_adopcion));

        if (adopcion_registrar(&a) == 0) {
            cargar_adopciones(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Adopcion registrada. La mascota ahora figura como adoptada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la adopcion.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void abrir_pantalla_adopciones(GtkWidget *padre, Rol rol) {
    ContextoAdopciones *ctx = g_malloc0(sizeof(ContextoAdopciones));
    ctx->rol = rol;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Control de Adopciones");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 720, 460);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Control de Adopciones</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_ADOPCIONES,
        G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_ADOPCIONES] = {"ID", "ID Mascota", "Adoptante", "Contacto", "Fecha"};
    for (int i = 0; i < N_COL_ADOPCIONES; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Ver listado");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar adopcion");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_adopciones_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_adopcion_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_adopciones(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Base de Donantes
 * ================================================================= */

enum {
    COL_D_ID = 0,
    COL_D_NOMBRE,
    COL_D_CONTACTO,
    COL_D_MONTO,
    COL_D_FECHA,
    N_COL_DONANTES
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    GtkWidget    *lbl_total;
} ContextoDonantes;

static void cargar_donantes(ContextoDonantes *ctx) {
    gtk_list_store_clear(ctx->store);

    Donante *ds;
    int n;
    if (donante_listar(&ds, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de donantes.", TRUE);
        return;
    }

    for (int i = 0; i < n; i++) {
        char monto_txt[32];
        snprintf(monto_txt, sizeof(monto_txt), "%.2f", ds[i].monto);

        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_D_ID, ds[i].id,
            COL_D_NOMBRE, ds[i].nombre,
            COL_D_CONTACTO, ds[i].contacto,
            COL_D_MONTO, monto_txt,
            COL_D_FECHA, ds[i].fecha,
            -1);
    }
    free(ds);

    char total_txt[64];
    snprintf(total_txt, sizeof(total_txt), "Total recaudado: %.2f", donante_total_recaudado());
    gtk_label_set_text(GTK_LABEL(ctx->lbl_total), total_txt);
}

static void on_refrescar_donantes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    cargar_donantes((ContextoDonantes *)datos);
}

static void on_registrar_donante_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoDonantes *ctx = (ContextoDonantes *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrar donante", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_nombre   = gtk_entry_new();
    GtkWidget *e_contacto = gtk_entry_new();
    GtkWidget *e_monto    = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_monto), "0.00");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre del donante:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Contacto:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_contacto, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Monto donado:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_monto, 1, 2, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Donante d;
        memset(&d, 0, sizeof(d));
        snprintf(d.nombre, sizeof(d.nombre), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(d.contacto, sizeof(d.contacto), "%s", gtk_entry_get_text(GTK_ENTRY(e_contacto)));
        d.monto = atof(gtk_entry_get_text(GTK_ENTRY(e_monto)));
        hoy(d.fecha, sizeof(d.fecha));

        if (donante_agregar(&d) == 0) {
            cargar_donantes(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Donante registrado.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar el donante.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void abrir_pantalla_donantes(GtkWidget *padre, Rol rol) {
    (void)rol; /* ya se filtro el acceso antes de llamar a esta funcion */

    ContextoDonantes *ctx = g_malloc0(sizeof(ContextoDonantes));

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Base de Donantes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 720, 460);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Base de Donantes</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_DONANTES,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_DONANTES] = {"ID", "Nombre", "Contacto", "Monto", "Fecha"};
    for (int i = 0; i < N_COL_DONANTES; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    ctx->lbl_total = gtk_label_new("Total recaudado: 0.00");
    gtk_widget_set_halign(ctx->lbl_total, GTK_ALIGN_END);
    gtk_box_pack_start(GTK_BOX(caja), ctx->lbl_total, FALSE, FALSE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Ver listado");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar donante");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_donantes_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_donante_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_donantes(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Reportes
 * ================================================================= */

typedef struct {
    GtkWidget *ventana;
    GtkWidget *vista_texto;
    GtkWidget *vista_historial;
    GtkWidget *lbl_estado;
    GtkWidget *btn_guardar;
} ContextoReportes;

static void mostrar_contenido_archivo(GtkTextView *vista, const char *ruta) {
    FILE *f = fopen(ruta, "r");
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(vista);
    if (!f) {
        gtk_text_buffer_set_text(buffer, "(no se pudo abrir el archivo para mostrarlo aqui)", -1);
        return;
    }
    GString *contenido = g_string_new(NULL);
    char linea[512];
    while (fgets(linea, sizeof(linea), f) != NULL) {
        g_string_append(contenido, linea);
    }
    fclose(f);
    gtk_text_buffer_set_text(buffer, contenido->str, -1);
    g_string_free(contenido, TRUE);
}

/* Escribe el contenido de texto plano de un reporte a un PDF simple:
 * fuente monoespaciada, una linea de texto por linea del reporte, con
 * paginacion automatica al llenarse la hoja (tamano carta). No hace
 * falta ninguna libreria nueva: usa Cairo, que ya viene con GTK3. */
static void dibujar_pie_pagina(cairo_t *cr, double ancho, double alto, double margen, int pagina) {
    cairo_save(cr);
    cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr, 8.0);
    cairo_set_source_rgb(cr, 0.55, 0.55, 0.55);

    cairo_move_to(cr, margen, alto - 20.0);
    cairo_show_text(cr, "PawOS Refugio");

    char texto_pagina[32];
    snprintf(texto_pagina, sizeof(texto_pagina), "Pagina %d", pagina);
    cairo_text_extents_t ext;
    cairo_text_extents(cr, texto_pagina, &ext);
    cairo_move_to(cr, ancho - margen - ext.width, alto - 20.0);
    cairo_show_text(cr, texto_pagina);

    cairo_restore(cr);
}

/* Escribe el reporte con un diseno mas profesional: el titulo
 * ("===== ... =====") se centra en verde institucional con una linea
 * debajo, la fecha de generacion sale en cursiva gris, los encabezados
 * de seccion ("-- ... --") salen en negrita, y cada pagina lleva un
 * pie con el nombre del sistema y el numero de pagina. El resto del
 * contenido sigue en monoespaciado, igual que antes. */
static gboolean escribir_pdf_simple(const char *ruta, const char *contenido) {
    const double ancho = 612.0, alto = 792.0; /* carta (Letter), en puntos */
    const double margen = 40.0;
    const double tam_fuente = 10.0;
    const double interlineado = 14.0;
    const double vr = 0.137, vg = 0.573, vb = 0.294; /* verde institucional PawOS */

    cairo_surface_t *superficie = cairo_pdf_surface_create(ruta, ancho, alto);
    if (cairo_surface_status(superficie) != CAIRO_STATUS_SUCCESS) {
        cairo_surface_destroy(superficie);
        return FALSE;
    }
    cairo_t *cr = cairo_create(superficie);

    int pagina = 1;
    double y = margen;

    gchar **lineas = g_strsplit(contenido, "\n", -1);
    for (int i = 0; lineas[i] != NULL; i++) {
        const char *linea = lineas[i];
        gboolean es_titulo = g_str_has_prefix(linea, "=====");
        gboolean es_encabezado = strlen(linea) > 4 && g_str_has_prefix(linea, "--") && g_str_has_suffix(linea, "--");
        gboolean es_fecha = g_str_has_prefix(linea, "Generado:");

        double alto_linea = interlineado;
        if (es_titulo) alto_linea = 26.0;
        else if (es_encabezado) alto_linea = 20.0;

        if (y + alto_linea > alto - margen) {
            dibujar_pie_pagina(cr, ancho, alto, margen, pagina);
            cairo_show_page(cr);
            pagina++;
            y = margen;
        }

        if (es_titulo) {
            gchar *texto = g_strdup(linea);
            g_strdelimit(texto, "=", ' ');
            gchar *texto_limpio = g_strstrip(texto);

            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 16.0);
            cairo_set_source_rgb(cr, vr, vg, vb);
            cairo_text_extents_t ext;
            cairo_text_extents(cr, texto_limpio, &ext);
            cairo_move_to(cr, (ancho - ext.width) / 2.0, y + 16.0);
            cairo_show_text(cr, texto_limpio);

            cairo_set_line_width(cr, 1.2);
            cairo_move_to(cr, margen, y + 24.0);
            cairo_line_to(cr, ancho - margen, y + 24.0);
            cairo_stroke(cr);

            g_free(texto);
            y += alto_linea;
        } else if (es_fecha) {
            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_ITALIC, CAIRO_FONT_WEIGHT_NORMAL);
            cairo_set_font_size(cr, 9.0);
            cairo_set_source_rgb(cr, 0.4, 0.4, 0.4);
            cairo_text_extents_t ext;
            cairo_text_extents(cr, linea, &ext);
            cairo_move_to(cr, (ancho - ext.width) / 2.0, y + 10.0);
            cairo_show_text(cr, linea);
            y += alto_linea;
        } else if (es_encabezado) {
            gchar *texto = g_strdup(linea);
            g_strdelimit(texto, "-", ' ');
            gchar *texto_limpio = g_strstrip(texto);

            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 11.5);
            cairo_set_source_rgb(cr, vr * 0.7, vg * 0.7, vb * 0.7);
            cairo_move_to(cr, margen, y + 14.0);
            cairo_show_text(cr, texto_limpio);

            g_free(texto);
            y += alto_linea;
        } else if (linea[0] == '\0') {
            y += alto_linea * 0.6;
        } else {
            cairo_select_font_face(cr, "Monospace", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
            cairo_set_font_size(cr, tam_fuente);
            cairo_set_source_rgb(cr, 0.1, 0.1, 0.1);
            cairo_move_to(cr, margen, y + 9.0);
            cairo_show_text(cr, linea);
            y += alto_linea;
        }
    }
    g_strfreev(lineas);

    dibujar_pie_pagina(cr, ancho, alto, margen, pagina);
    cairo_show_page(cr);
    cairo_status_t estado = cairo_status(cr);
    cairo_destroy(cr);
    cairo_surface_destroy(superficie);
    return estado == CAIRO_STATUS_SUCCESS;
}

static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoReportes *ctx = (ContextoReportes *)datos;

    const char *ruta_principal = "/var/pawos/reportes/reporte_actual.txt";
    const char *ruta_usada = NULL;

    if (reporte_generar(ruta_principal) == 0) {
        ruta_usada = ruta_principal;
    } else if (reporte_generar("reporte_actual.txt") == 0) {
        ruta_usada = "reporte_actual.txt";
    }

    if (ruta_usada == NULL) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), "No se pudo generar el reporte.");
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo generar el reporte.", TRUE);
        return;
    }

    char estado_txt[200];
    snprintf(estado_txt, sizeof(estado_txt), "Reporte generado en: %s", ruta_usada);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), estado_txt);
    mostrar_contenido_archivo(GTK_TEXT_VIEW(ctx->vista_texto), ruta_usada);
    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);
}

/* Abre el dialogo estandar de "Guardar archivo" de GTK (el usuario
 * elige carpeta y nombre libremente, no queda forzado a la ruta fija
 * del sistema) y guarda el reporte ya generado como .txt o .pdf, segun
 * el filtro que elija o la extension que escriba. */
static void on_guardar_como_reporte_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoReportes *ctx = (ContextoReportes *)datos;

    GtkWidget *dialogo = gtk_file_chooser_dialog_new(
        "Guardar reporte como...", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_SAVE,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_do_overwrite_confirmation(GTK_FILE_CHOOSER(dialogo), TRUE);
    gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(dialogo), "reporte_pawos.txt");

    const char *carpeta_inicial = g_get_home_dir();
    if (carpeta_inicial != NULL) {
        gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(dialogo), carpeta_inicial);
    }

    GtkFileFilter *filtro_txt = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro_txt, "Texto (*.txt)");
    gtk_file_filter_add_pattern(filtro_txt, "*.txt");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro_txt);

    GtkFileFilter *filtro_pdf = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro_pdf, "PDF (*.pdf)");
    gtk_file_filter_add_pattern(filtro_pdf, "*.pdf");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro_pdf);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(dialogo);
        return;
    }

    gchar *ruta_elegida = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialogo));
    GtkFileFilter *filtro_activo = gtk_file_chooser_get_filter(GTK_FILE_CHOOSER(dialogo));
    gtk_widget_destroy(dialogo);
    if (ruta_elegida == NULL) return;

    gboolean quiere_pdf = (filtro_activo == filtro_pdf) || g_str_has_suffix(ruta_elegida, ".pdf");

    /* Siempre normalizamos la extension segun el formato elegido, sin
     * importar la extension del nombre sugerido por el dialogo. Antes,
     * si el usuario elegia el filtro PDF pero no cambiaba el nombre
     * por defecto "reporte_pawos.txt", el archivo se guardaba con
     * extension .txt aunque el contenido fuera PDF (por eso "no
     * funcionaba" el boton de PDF). */
    gchar *ruta_sin_extension = g_strdup(ruta_elegida);
    if (g_str_has_suffix(ruta_sin_extension, ".pdf") || g_str_has_suffix(ruta_sin_extension, ".txt")) {
        ruta_sin_extension[strlen(ruta_sin_extension) - 4] = '\0';
    }
    gchar *ruta_final = g_strconcat(ruta_sin_extension, quiere_pdf ? ".pdf" : ".txt", NULL);
    g_free(ruta_sin_extension);
    g_free(ruta_elegida);

    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(ctx->vista_texto));
    GtkTextIter inicio, fin;
    gtk_text_buffer_get_bounds(buffer, &inicio, &fin);
    gchar *contenido_reporte = gtk_text_buffer_get_text(buffer, &inicio, &fin, FALSE);

    gboolean ok;
    if (quiere_pdf) {
        ok = escribir_pdf_simple(ruta_final, contenido_reporte);
    } else {
        GError *error = NULL;
        ok = g_file_set_contents(ruta_final, contenido_reporte, -1, &error);
        if (error) g_error_free(error);
    }

    if (ok) {
        char msg[600];
        snprintf(msg, sizeof(msg), "Reporte guardado en:\n%s", ruta_final);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar el reporte en esa ubicacion.", TRUE);
    }

    g_free(contenido_reporte);
    g_free(ruta_final);
}

/* ---- Historial de reportes generados (bitacora persistente) ---- */

static void cargar_historial(ContextoReportes *ctx) {
    const char *rutas[2] = { "/var/pawos/reportes/historial_reportes.log", "historial_reportes.log" };
    FILE *f = NULL;
    for (int i = 0; i < 2 && f == NULL; i++) f = fopen(rutas[i], "r");

    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(ctx->vista_historial));
    if (!f) {
        gtk_text_buffer_set_text(buffer, "Todavia no hay reportes registrados.", -1);
        return;
    }

    GPtrArray *lineas = g_ptr_array_new_with_free_func(g_free);
    char linea[256];
    while (fgets(linea, sizeof(linea), f) != NULL) {
        g_ptr_array_add(lineas, g_strdup(linea));
    }
    fclose(f);

    GString *texto = g_string_new(NULL);
    if (lineas->len == 0) {
        g_string_append(texto, "Todavia no hay reportes registrados.");
    } else {
        for (int i = (int)lineas->len - 1; i >= 0; i--) {
            g_string_append(texto, (const char *)g_ptr_array_index(lineas, i));
        }
    }
    gtk_text_buffer_set_text(buffer, texto->str, -1);
    g_string_free(texto, TRUE);
    g_ptr_array_free(lineas, TRUE);
}

static void agregar_entrada_historial(ContextoReportes *ctx, const char *tipo) {
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    char linea[256];
    snprintf(linea, sizeof(linea), "%s - Reporte de %s\n", fecha, tipo);

    FILE *f = fopen("/var/pawos/reportes/historial_reportes.log", "a");
    if (!f) f = fopen("historial_reportes.log", "a");
    if (f) {
        fputs(linea, f);
        fclose(f);
    }

    cargar_historial(ctx);
}

/* ---- Reportes individuales por categoria ---- */

typedef struct {
    ContextoReportes *ctx;
    const char *nombre_tipo;
    int (*generador)(const char *ruta_salida);
    const char *ruta_fija;
    const char *ruta_relativa;
} DatosReporteCategoria;

static void on_generar_reporte_categoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosReporteCategoria *d = (DatosReporteCategoria *)datos;
    ContextoReportes *ctx = d->ctx;

    const char *ruta_usada = NULL;
    if (d->generador(d->ruta_fija) == 0) {
        ruta_usada = d->ruta_fija;
    } else if (d->generador(d->ruta_relativa) == 0) {
        ruta_usada = d->ruta_relativa;
    }

    if (ruta_usada == NULL) {
        char msg[200];
        snprintf(msg, sizeof(msg), "No se pudo generar el reporte de %s.", d->nombre_tipo);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
        return;
    }

    char estado_txt[220];
    snprintf(estado_txt, sizeof(estado_txt), "Reporte de %s generado en: %s", d->nombre_tipo, ruta_usada);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), estado_txt);
    mostrar_contenido_archivo(GTK_TEXT_VIEW(ctx->vista_texto), ruta_usada);
    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);

    agregar_entrada_historial(ctx, d->nombre_tipo);
}

static void abrir_pantalla_reportes(GtkWidget *padre, Rol rol) {
    (void)rol; /* ya se filtro el acceso antes de llamar a esta funcion */

    ContextoReportes *ctx = g_malloc0(sizeof(ContextoReportes));

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Reportes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 640, 480);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Reportes</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "Genera un resumen del estado del refugio (mascotas, vacunas, adopciones y donantes)\n"
        "en un archivo de texto dentro del sistema.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *btn_generar = gtk_button_new_with_label("Generar reporte");
    gtk_widget_set_halign(btn_generar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_generar, FALSE, FALSE, 0);

    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);

    GtkWidget *lbl_categorias = gtk_label_new("Reportes por categoria:");
    gtk_widget_set_halign(lbl_categorias, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_categorias, FALSE, FALSE, 4);

    GtkWidget *caja_categorias = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(caja), caja_categorias, FALSE, FALSE, 0);

    static const char *nombres_categorias[5] = {
        "Mascotas", "Vacunas", "Adopciones", "Donantes", "Alertas de Sensores"
    };
    static const char *rutas_fijas_categorias[5] = {
        "/var/pawos/reportes/reporte_mascotas.txt",
        "/var/pawos/reportes/reporte_vacunas.txt",
        "/var/pawos/reportes/reporte_adopciones.txt",
        "/var/pawos/reportes/reporte_donantes.txt",
        "/var/pawos/reportes/reporte_alertas.txt"
    };
    static const char *rutas_relativas_categorias[5] = {
        "reporte_mascotas.txt", "reporte_vacunas.txt", "reporte_adopciones.txt",
        "reporte_donantes.txt", "reporte_alertas.txt"
    };
    int (*generadores_categorias[5])(const char *) = {
        reporte_generar_mascotas, reporte_generar_vacunas, reporte_generar_adopciones,
        reporte_generar_donantes, reporte_generar_alertas
    };
    for (int i = 0; i < 5; i++) {
        GtkWidget *btn_cat = gtk_button_new_with_label(nombres_categorias[i]);
        gtk_box_pack_start(GTK_BOX(caja_categorias), btn_cat, FALSE, FALSE, 0);
        DatosReporteCategoria *d = g_new0(DatosReporteCategoria, 1);
        d->ctx = ctx;
        d->nombre_tipo = nombres_categorias[i];
        d->generador = generadores_categorias[i];
        d->ruta_fija = rutas_fijas_categorias[i];
        d->ruta_relativa = rutas_relativas_categorias[i];
        g_signal_connect(btn_cat, "clicked", G_CALLBACK(on_generar_reporte_categoria_clicked), d);
    }

    ctx->lbl_estado = gtk_label_new("Todavia no se ha generado ningun reporte en esta sesion.");
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), ctx->lbl_estado, FALSE, FALSE, 0);

    ctx->vista_texto = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_texto), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_texto), TRUE);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->vista_texto);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *lbl_historial = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_historial), "<b>Historial de reportes generados</b>");
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_historial, FALSE, FALSE, 4);

    ctx->vista_historial = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_historial), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_historial), TRUE);
    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 110);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->vista_historial);
    gtk_box_pack_start(GTK_BOX(caja), scroll_historial, FALSE, FALSE, 0);
    cargar_historial(ctx);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    gtk_widget_set_halign(btn_cerrar, GTK_ALIGN_END);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_generar, "clicked", G_CALLBACK(on_generar_reporte_clicked), ctx);
    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Administracion de Procesos (solo Administrador)
 * ================================================================= */

enum {
    COL_P_PID = 0,
    COL_P_NOMBRE,
    COL_P_ESTADO,
    N_COL_PROCESOS
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
} ContextoProcesos;

static void cargar_procesos(ContextoProcesos *ctx) {
    gtk_list_store_clear(ctx->store);

    ProcesoInfo lista[PROCESOS_MAX];
    int total = procesos_obtener_lista(lista, PROCESOS_MAX);
    if (total < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de procesos (/proc).", TRUE);
        return;
    }

    for (int i = 0; i < total; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_P_PID, lista[i].pid,
            COL_P_NOMBRE, lista[i].nombre,
            COL_P_ESTADO, lista[i].estado,
            -1);
    }
}

static void on_refrescar_procesos_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    cargar_procesos((ContextoProcesos *)datos);
}

static void on_crear_proceso_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoProcesos *ctx = (ContextoProcesos *)datos;

    int pid_hijo = procesos_crear_ejemplo();
    if (pid_hijo < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error: no se pudo crear el proceso (fork fallo).", TRUE);
    } else {
        char msg[128];
        snprintf(msg, sizeof(msg),
            "Proceso hijo creado correctamente.\nPID del nuevo proceso: %d", pid_hijo);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
        cargar_procesos(ctx);
    }
}

static void on_terminar_proceso_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoProcesos *ctx = (ContextoProcesos *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Terminar un proceso", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Enviar senal", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    GtkWidget *lbl_pid = gtk_label_new("PID del proceso a terminar:");
    gtk_widget_set_halign(lbl_pid, GTK_ALIGN_START);
    GtkWidget *e_pid = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(e_pid), GTK_INPUT_PURPOSE_DIGITS);

    GtkWidget *chk_forzar = gtk_check_button_new_with_label("Forzar cierre (SIGKILL en lugar de SIGTERM)");

    gtk_box_pack_start(GTK_BOX(caja), lbl_pid, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), e_pid, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), chk_forzar, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        int pid = atoi(gtk_entry_get_text(GTK_ENTRY(e_pid)));
        int forzar = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(chk_forzar)) ? 1 : 0;

        errno = 0;
        int resultado = procesos_terminar(pid, forzar);

        if (resultado == 0) {
            char msg[96];
            snprintf(msg, sizeof(msg), "Senal enviada correctamente al proceso %d.", pid);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
        } else {
            char msg[192];
            const char *motivo;
            if (errno == ESRCH) motivo = "ese proceso no existe (ya termino o el PID es incorrecto)";
            else if (errno == EPERM) motivo = "no tiene permisos para terminar ese proceso";
            else motivo = "PID invalido";
            snprintf(msg, sizeof(msg), "No se pudo terminar el proceso %d.\nMotivo: %s.", pid, motivo);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
        }
        cargar_procesos(ctx);
    }
    gtk_widget_destroy(dialogo);
}

static void abrir_pantalla_procesos(GtkWidget *padre) {
    ContextoProcesos *ctx = g_malloc0(sizeof(ContextoProcesos));

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Administracion de Procesos");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 700, 460);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Administracion de Procesos</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_PROCESOS, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_PROCESOS] = {"PID", "Nombre", "Estado"};
    for (int i = 0; i < N_COL_PROCESOS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_crear     = gtk_button_new_with_label("Crear proceso de ejemplo (fork)");
    GtkWidget *btn_terminar  = gtk_button_new_with_label("Terminar proceso");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_crear, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_terminar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_procesos_clicked), ctx);
    g_signal_connect(btn_crear, "clicked", G_CALLBACK(on_crear_proceso_clicked), ctx);
    g_signal_connect(btn_terminar, "clicked", G_CALLBACK(on_terminar_proceso_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_procesos(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Administracion de Memoria (solo Administrador)
 * ================================================================= */

typedef struct {
    GtkWidget *ventana;
    GtkWidget *lbl_total;
    GtkWidget *lbl_paginas_totales;
    GtkWidget *lbl_paginas_usadas;
    GtkWidget *lbl_paginas_libres;
    GtkWidget *lbl_page_faults;
    GtkWidget *lbl_swaps;
    gboolean   proceso_demo_creado;
    void      *direccion_demo;
} ContextoMemoria;

static void actualizar_estadisticas_memoria(ContextoMemoria *ctx) {
    estadisticas_memoria_t est = memoria_obtener_estadisticas();
    char buf[64];

    snprintf(buf, sizeof(buf), "Memoria total: %u KB", est.memoria_total_bytes / 1024);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_total), buf);

    snprintf(buf, sizeof(buf), "Paginas totales: %u", est.paginas_totales);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_paginas_totales), buf);

    snprintf(buf, sizeof(buf), "Paginas usadas: %u", est.paginas_usadas);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_paginas_usadas), buf);

    snprintf(buf, sizeof(buf), "Paginas libres: %u", est.paginas_libres);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_paginas_libres), buf);

    snprintf(buf, sizeof(buf), "Page faults: %u", est.page_faults);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_page_faults), buf);

    snprintf(buf, sizeof(buf), "Swaps realizados: %u", est.swaps_realizados);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_swaps), buf);
}

static void on_refrescar_memoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    actualizar_estadisticas_memoria((ContextoMemoria *)datos);
}

static void on_crear_proceso_demo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMemoria *ctx = (ContextoMemoria *)datos;

    if (ctx->proceso_demo_creado) {
        char msg[96];
        snprintf(msg, sizeof(msg), "Ya existe un proceso de ejemplo activo (ID %u).", ID_PROCESO_DEMO);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
        return;
    }

    tabla_paginas_t *tabla = memoria_crear_proceso(ID_PROCESO_DEMO);
    if (tabla == NULL) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error: no se pudo crear el proceso de ejemplo.", TRUE);
    } else {
        ctx->proceso_demo_creado = TRUE;
        char msg[96];
        snprintf(msg, sizeof(msg), "Proceso de ejemplo creado (ID %u) con su tabla de paginas.", ID_PROCESO_DEMO);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
    }
    actualizar_estadisticas_memoria(ctx);
}

static void on_asignar_memoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMemoria *ctx = (ContextoMemoria *)datos;

    if (!ctx->proceso_demo_creado) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Primero cree el proceso de ejemplo.", TRUE);
        return;
    }

    int bytes;
    if (!pedir_entero_dialog(GTK_WINDOW(ctx->ventana), "Asignar memoria", "Cuantos bytes desea asignar?", &bytes))
        return;

    void *direccion = memoria_asignar(ID_PROCESO_DEMO, (uint32_t)bytes);
    if (direccion == NULL) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error: no se pudo asignar memoria (sin espacio disponible).", TRUE);
    } else {
        ctx->direccion_demo = direccion;
        char msg[96];
        snprintf(msg, sizeof(msg), "Memoria asignada correctamente en direccion virtual %p.", direccion);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
    }
    actualizar_estadisticas_memoria(ctx);
}

static void on_probar_lectura_escritura_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMemoria *ctx = (ContextoMemoria *)datos;

    if (!ctx->proceso_demo_creado || ctx->direccion_demo == NULL) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Primero cree el proceso y asigne memoria.", TRUE);
        return;
    }

    int valor;
    if (!pedir_entero_dialog(GTK_WINDOW(ctx->ventana), "Probar escritura/lectura", "Valor a escribir (0-255):", &valor))
        return;

    memoria_escribir_byte(ID_PROCESO_DEMO, ctx->direccion_demo, (uint8_t)valor);
    uint8_t leido = memoria_leer_byte(ID_PROCESO_DEMO, ctx->direccion_demo);

    char msg[128];
    snprintf(msg, sizeof(msg), "Valor escrito: %d\nValor leido: %u %s",
             valor, leido, (leido == (uint8_t)valor) ? "(coincide)" : "(no coincide)");
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
}

static void on_destruir_proceso_demo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMemoria *ctx = (ContextoMemoria *)datos;

    if (!ctx->proceso_demo_creado) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No hay ningun proceso de ejemplo activo.", TRUE);
        return;
    }

    memoria_destruir_proceso(ID_PROCESO_DEMO);
    ctx->proceso_demo_creado = FALSE;
    ctx->direccion_demo = NULL;

    mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Proceso de ejemplo destruido, memoria liberada.", FALSE);
    actualizar_estadisticas_memoria(ctx);
}

static void abrir_pantalla_memoria(GtkWidget *padre) {
    ContextoMemoria *ctx = g_malloc0(sizeof(ContextoMemoria));

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Administracion de Memoria");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 520, 420);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 16);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Administracion de Memoria</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *marco_stats = gtk_frame_new("Estadisticas de memoria");
    GtkWidget *caja_stats = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_container_set_border_width(GTK_CONTAINER(caja_stats), 10);
    gtk_container_add(GTK_CONTAINER(marco_stats), caja_stats);

    ctx->lbl_total            = gtk_label_new("Memoria total: -");
    ctx->lbl_paginas_totales  = gtk_label_new("Paginas totales: -");
    ctx->lbl_paginas_usadas   = gtk_label_new("Paginas usadas: -");
    ctx->lbl_paginas_libres   = gtk_label_new("Paginas libres: -");
    ctx->lbl_page_faults      = gtk_label_new("Page faults: -");
    ctx->lbl_swaps            = gtk_label_new("Swaps realizados: -");

    GtkWidget *etiquetas_stats[] = {
        ctx->lbl_total, ctx->lbl_paginas_totales, ctx->lbl_paginas_usadas,
        ctx->lbl_paginas_libres, ctx->lbl_page_faults, ctx->lbl_swaps
    };
    for (unsigned i = 0; i < G_N_ELEMENTS(etiquetas_stats); i++) {
        gtk_widget_set_halign(etiquetas_stats[i], GTK_ALIGN_START);
        gtk_box_pack_start(GTK_BOX(caja_stats), etiquetas_stats[i], FALSE, FALSE, 0);
    }
    gtk_box_pack_start(GTK_BOX(caja), marco_stats, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar estadisticas");
    gtk_widget_set_halign(btn_refrescar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_refrescar, FALSE, FALSE, 0);

    GtkWidget *marco_demo = gtk_frame_new("Proceso de ejemplo");
    GtkWidget *caja_demo = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_demo), 10);
    gtk_container_add(GTK_CONTAINER(marco_demo), caja_demo);

    GtkWidget *btn_crear     = gtk_button_new_with_label("Crear proceso de ejemplo");
    GtkWidget *btn_asignar   = gtk_button_new_with_label("Asignar memoria al proceso");
    GtkWidget *btn_probar    = gtk_button_new_with_label("Probar escritura/lectura");
    GtkWidget *btn_destruir  = gtk_button_new_with_label("Destruir proceso de ejemplo");

    gtk_box_pack_start(GTK_BOX(caja_demo), btn_crear, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_demo), btn_asignar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_demo), btn_probar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_demo), btn_destruir, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), marco_demo, FALSE, FALSE, 0);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    gtk_widget_set_halign(btn_cerrar, GTK_ALIGN_END);
    gtk_box_pack_end(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_memoria_clicked), ctx);
    g_signal_connect(btn_crear, "clicked", G_CALLBACK(on_crear_proceso_demo_clicked), ctx);
    g_signal_connect(btn_asignar, "clicked", G_CALLBACK(on_asignar_memoria_clicked), ctx);
    g_signal_connect(btn_probar, "clicked", G_CALLBACK(on_probar_lectura_escritura_clicked), ctx);
    g_signal_connect(btn_destruir, "clicked", G_CALLBACK(on_destruir_proceso_demo_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    actualizar_estadisticas_memoria(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Respaldo en la Nube
 *
 * El respaldo real (base de datos -> Google Drive via rclone) ya corre
 * automaticamente cada noche mediante el temporizador de systemd
 * pawos-backup.timer / pawos-backup.service instalado por
 * instalar-pawos.sh. Este modulo de la GUI no reimplementa ese
 * respaldo: solo consulta su estado (accion de lectura, sin permisos
 * especiales) y permite dispararlo manualmente antes de la hora
 * programada (accion que si requiere permisos, ver nota de sudoers
 * mas abajo).
 * ================================================================= */

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *lbl_ultimo;
    GtkWidget    *lbl_estado;
    GtkWidget    *lbl_modo;
    GtkWidget    *radio_auto;
    GtkWidget    *radio_manual;
    GtkWidget    *combo_intervalo;
    GtkWidget    *lista_historial;
    GtkListStore *modelo_historial;
    GtkWidget    *btn_restaurar;
    GtkWidget    *btn_actualizar;
    GtkWidget    *entrada_etiqueta_auto; /* etiqueta por defecto: se usa
                                           * si "Respaldar ahora" se deja
                                           * en blanco, y en el respaldo
                                           * automatico (que no tiene
                                           * forma de pedir una a nadie) */
    gboolean      cargando_historial; /* evita apilar varias cargas si se
                                        * presiona "Actualizar estado" muy
                                        * seguido mientras una ya esta en
                                        * curso */
    gboolean     *vivo; /* TRUE mientras la ventana existe; los hilos en
                          * segundo plano la revisan antes de tocar el
                          * contexto, por si la ventana se cierra mientras
                          * una operacion de red (listar/restaurar) sigue
                          * en curso. Nunca se libera (una gboolean suelta
                          * por apertura de esta pantalla, a proposito). */
    Rol           rol;
} ContextoRespaldo;

/* Los valores del combo de intervalo, en horas: 1 dia, 3 dias,
 * 1 semana, 1 mes (aprox. 30 dias). El indice del combo coincide con
 * el indice de este arreglo. */
static const int INTERVALOS_HORAS[] = { 24, 72, 168, 720 };
static const char *INTERVALOS_ETIQUETA[] = {
    "Cada 1 dia", "Cada 3 dias", "Cada 1 semana", "Cada 1 mes"
};
#define N_INTERVALOS 4

/* Columnas del historial de respaldos (lo que 'pawos-listar-respaldos'
 * reporta que hay guardado en Google Drive). COL_HIST_ARCHIVO no se
 * muestra en la tabla, pero se guarda en el modelo para saber
 * exactamente que archivo pedir de vuelta al restaurar. COL_HIST_FECHA
 * ya viene en hora local (no UTC) desde el script. COL_HIST_ETIQUETA es
 * el nombre opcional que se le puso al respaldo con "Respaldar ahora"
 * (vacio en los respaldos automaticos, que nunca llevan etiqueta). */
enum {
    COL_HIST_FECHA = 0,
    COL_HIST_TAMANO,
    COL_HIST_ARCHIVO,
    COL_HIST_ETIQUETA,
    N_COL_HIST
};

/* Ejecuta 'comando', lee la primera linea de su salida en 'out' (sin
 * salto de linea) y la deja vacia si algo fallo. */
static void leer_salida_comando(const char *comando, char *out, size_t out_len) {
    out[0] = '\0';
    FILE *p = popen(comando, "r");
    if (!p) return;
    if (fgets(out, (int)out_len, p) != NULL) {
        size_t len = strlen(out);
        while (len > 0 && (out[len - 1] == '\n' || out[len - 1] == '\r')) {
            out[--len] = '\0';
        }
    }
    pclose(p);
}

static void actualizar_estado_respaldo(ContextoRespaldo *ctx) {
    char estado[64], resultado[64], ultimo[160];

    leer_salida_comando(
        "systemctl show pawos-backup.service --value -p ActiveState 2>/dev/null",
        estado, sizeof(estado));
    leer_salida_comando(
        "systemctl show pawos-backup.service --value -p Result 2>/dev/null",
        resultado, sizeof(resultado));
    leer_salida_comando(
        "systemctl show pawos-backup.timer --value -p LastTriggerUSec 2>/dev/null",
        ultimo, sizeof(ultimo));

    char buf[220];
    snprintf(buf, sizeof(buf), "Ultimo respaldo automatico: %s",
             ultimo[0] ? ultimo : "sin datos todavia (el temporizador no se ha disparado en esta maquina)");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_ultimo), buf);

    snprintf(buf, sizeof(buf), "Estado del servicio: %s   |   Resultado: %s",
             estado[0] ? estado : "desconocido", resultado[0] ? resultado : "desconocido");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), buf);
}

/* Lee /var/pawos/backup_modo.txt (lo escribe pawos-configurar-respaldo)
 * y ajusta los radio buttons / combo para reflejar el modo actual. Si
 * el archivo no existe todavia (instalacion recien hecha, nunca se ha
 * cambiado el modo), se asume Automatico cada 1 dia (el valor por
 * defecto que deja instalar-pawos.sh). */
static void actualizar_ui_modo_respaldo(ContextoRespaldo *ctx) {
    char linea[64];
    leer_salida_comando("cat /var/pawos/backup_modo.txt 2>/dev/null", linea, sizeof(linea));

    int es_manual = (strncmp(linea, "manual", 6) == 0);
    int horas = 24;
    if (!es_manual) {
        const char *dos_puntos = strchr(linea, ':');
        if (dos_puntos && *(dos_puntos + 1)) horas = atoi(dos_puntos + 1);
    }

    int indice = 0;
    for (int i = 0; i < N_INTERVALOS; i++) {
        if (INTERVALOS_HORAS[i] == horas) { indice = i; break; }
    }

    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(es_manual ? ctx->radio_manual : ctx->radio_auto), TRUE);
    gtk_combo_box_set_active(GTK_COMBO_BOX(ctx->combo_intervalo), indice);
    gtk_widget_set_sensitive(ctx->combo_intervalo, !es_manual);

    char buf[96];
    snprintf(buf, sizeof(buf), "Modo actual: %s",
             es_manual ? "Manual" : INTERVALOS_ETIQUETA[indice]);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_modo), buf);

    char etiqueta_guardada[64];
    leer_salida_comando("cat /var/pawos/backup_etiqueta_auto.txt 2>/dev/null",
        etiqueta_guardada, sizeof(etiqueta_guardada));
    gtk_entry_set_text(GTK_ENTRY(ctx->entrada_etiqueta_auto), etiqueta_guardada);
}

/* Lee el registro de respaldos que ya existen en Google Drive (lo que
 * imprime 'pawos-listar-respaldos': una linea por archivo, con
 * TABULADOR entre columnas -"<fecha hora local>\t<tamano>\t<archivo>\t<etiqueta>"-,
 * no espacios, porque la fecha misma trae un espacio adentro) y llena
 * la tabla del historial con eso. Si el comando falla (por ejemplo,
 * porque todavia no existe el permiso sudo o rclone no esta
 * configurado), la tabla simplemente queda vacia.
 *
 * Importante: la fecha que se muestra es la de modificacion en Drive,
 * ya convertida a la hora local de esta maquina, no algo derivado del
 * nombre del archivo - dos respaldos distintos pueden mostrar la misma
 * fecha aqui. Por eso ARCHIVO siempre se guarda aparte (columna oculta)
 * y es lo unico que se usa para restaurar; nunca hay que reconstruir el
 * nombre a mano a partir
 * de lo que se ve en la columna de fecha.
 *
 * Esto habla con Google Drive (via 'pawos-listar-respaldos'), asi que
 * puede tardar unos segundos. Corre en un hilo aparte (g_thread_new)
 * para no congelar la ventana mientras espera - si esto corriera en el
 * hilo principal de GTK, el gestor de ventanas termina mostrando
 * "no responde" cada vez que la red tarda. El resultado se aplica de
 * vuelta a la UI con g_idle_add, que si corre en el hilo principal
 * (es la unica forma segura de tocar widgets de GTK desde otro hilo). */
typedef struct {
    ContextoRespaldo *ctx;
    gboolean         *vivo;
    GPtrArray        *lineas; /* char* strdup'd, una por respaldo */
} TareaHistorial;

static gboolean aplicar_historial_ui(gpointer datos) {
    TareaHistorial *t = (TareaHistorial *)datos;

    if (*t->vivo) {
        ContextoRespaldo *ctx = t->ctx;
        gtk_list_store_clear(ctx->modelo_historial);

        for (guint i = 0; i < t->lineas->len; i++) {
            char *linea = (char *)g_ptr_array_index(t->lineas, i);

            char *fecha = linea;
            char *tab1 = strchr(linea, '\t');
            if (!tab1) continue;
            *tab1 = '\0';
            char *tamano = tab1 + 1;
            char *tab2 = strchr(tamano, '\t');
            if (!tab2) continue;
            *tab2 = '\0';
            char *archivo = tab2 + 1;
            char *tab3 = strchr(archivo, '\t');
            char *etiqueta = "";
            if (tab3) {
                *tab3 = '\0';
                etiqueta = tab3 + 1;
            }
            if (archivo[0] == '\0') continue;

            GtkTreeIter iter;
            gtk_list_store_append(ctx->modelo_historial, &iter);
            gtk_list_store_set(ctx->modelo_historial, &iter,
                COL_HIST_FECHA, fecha,
                COL_HIST_TAMANO, tamano,
                COL_HIST_ARCHIVO, archivo,
                COL_HIST_ETIQUETA, etiqueta,
                -1);
        }
        ctx->cargando_historial = FALSE;
        if (ctx->btn_actualizar) gtk_widget_set_sensitive(ctx->btn_actualizar, TRUE);
    }

    g_ptr_array_free(t->lineas, TRUE);
    g_free(t);
    return G_SOURCE_REMOVE;
}

static gpointer hilo_listar_respaldos(gpointer datos) {
    TareaHistorial *t = (TareaHistorial *)datos;

    FILE *p = popen("sudo -n /usr/local/bin/pawos-listar-respaldos 2>/dev/null", "r");
    if (p) {
        char linea[256];
        while (fgets(linea, sizeof(linea), p) != NULL) {
            size_t len = strlen(linea);
            while (len > 0 && (linea[len - 1] == '\n' || linea[len - 1] == '\r')) linea[--len] = '\0';
            if (len > 0) g_ptr_array_add(t->lineas, g_strdup(linea));
        }
        pclose(p);
    }

    g_idle_add(aplicar_historial_ui, t);
    return NULL;
}

static void cargar_historial_respaldos(ContextoRespaldo *ctx) {
    if (ctx->cargando_historial) return; /* ya hay una carga en curso */
    ctx->cargando_historial = TRUE;
    if (ctx->btn_actualizar) gtk_widget_set_sensitive(ctx->btn_actualizar, FALSE);

    TareaHistorial *t = g_new0(TareaHistorial, 1);
    t->ctx = ctx;
    t->vivo = ctx->vivo;
    t->lineas = g_ptr_array_new_with_free_func(g_free);
    g_thread_new("pawos-listar-respaldos", hilo_listar_respaldos, t);
}

static void on_radio_modo_respaldo_toggled(GtkToggleButton *boton, gpointer datos) {
    (void)boton;
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;
    gboolean automatico = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(ctx->radio_auto));
    gtk_widget_set_sensitive(ctx->combo_intervalo, automatico);
}

static void on_guardar_config_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;

    if (ctx->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Requiere rol Administrador.", TRUE);
        return;
    }

    char comando[160];
    if (gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(ctx->radio_manual))) {
        snprintf(comando, sizeof(comando), "sudo -n /usr/local/bin/pawos-configurar-respaldo manual");
    } else {
        int indice = gtk_combo_box_get_active(GTK_COMBO_BOX(ctx->combo_intervalo));
        if (indice < 0) indice = 0;
        snprintf(comando, sizeof(comando),
                 "sudo -n /usr/local/bin/pawos-configurar-respaldo auto %d",
                 INTERVALOS_HORAS[indice]);
    }

    int rc = system(comando);

    /* Etiqueta por defecto: se escribe directo (sin sudo) porque
     * /var/pawos es escribible por el grupo "pawos-refugio", al que
     * pertenece admin_refugio (ver instalar-pawos.sh, seccion 6). Un
     * archivo vacio equivale a "sin etiqueta por defecto" -
     * pawos-backup-nube ya maneja ese caso. */
    const char *etiqueta_auto = gtk_entry_get_text(GTK_ENTRY(ctx->entrada_etiqueta_auto));
    FILE *fp = fopen("/var/pawos/backup_etiqueta_auto.txt", "w");
    if (fp) {
        fprintf(fp, "%s\n", etiqueta_auto);
        fclose(fp);
    }

    if (rc == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Configuracion de respaldo guardada.", FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "No se pudo guardar la configuracion.\n"
            "Verifica el permiso sudo (NOPASSWD) para\n"
            "'pawos-configurar-respaldo' (ver README.md).", TRUE);
    }
    actualizar_ui_modo_respaldo(ctx);
    actualizar_estado_respaldo(ctx);
}

static void on_actualizar_estado_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;
    actualizar_estado_respaldo(ctx);
    cargar_historial_respaldos(ctx);
}

/* Igual que el historial: restaurar habla con Google Drive (descarga el
 * archivo elegido), asi que puede tardar. Corre en un hilo aparte para
 * no congelar la ventana - de lo contrario el gestor de ventanas la
 * marca como "no responde" mientras dura la descarga. */
typedef struct {
    ContextoRespaldo *ctx;
    gboolean         *vivo;
    char             *archivo;
    int               rc; /* resultado de system(), llenado por el hilo */
} TareaRestaurar;

static gboolean aplicar_restaurar_ui(gpointer datos) {
    TareaRestaurar *t = (TareaRestaurar *)datos;

    if (*t->vivo) {
        ContextoRespaldo *ctx = t->ctx;
        gtk_widget_set_sensitive(ctx->btn_restaurar, TRUE);

        if (t->rc == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "Base de datos restaurada desde el respaldo seleccionado.\n"
                "Cierra y vuelve a abrir PawOS para ver los datos restaurados.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "No se pudo restaurar.\n"
                "Verifica el permiso sudo (NOPASSWD) para\n"
                "'pawos-restaurar-nube' (ver README.md).", TRUE);
        }
        cargar_historial_respaldos(ctx);
    }

    g_free(t->archivo);
    g_free(t);
    return G_SOURCE_REMOVE;
}

static gpointer hilo_restaurar_respaldo(gpointer datos) {
    TareaRestaurar *t = (TareaRestaurar *)datos;

    char comando[220];
    snprintf(comando, sizeof(comando), "sudo -n /usr/local/bin/pawos-restaurar-nube '%s'", t->archivo);
    t->rc = system(comando);

    g_idle_add(aplicar_restaurar_ui, t);
    return NULL;
}

/* Restaurar un respaldo pisa la base de datos actual, asi que: exige rol
 * Administrador, exige que haya algo seleccionado en la tabla del
 * historial, y pide confirmacion explicita antes de ejecutar nada. El
 * script 'pawos-restaurar-nube' (ver instalar-pawos.sh) ya se encarga
 * de guardar una copia de seguridad de la base de datos actual antes de
 * sobreescribirla, como red de seguridad adicional. */
static void on_restaurar_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;

    if (ctx->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Requiere rol Administrador.", TRUE);
        return;
    }

    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(ctx->lista_historial));
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "Selecciona un respaldo de la tabla de historial antes de restaurar.", TRUE);
        return;
    }

    gchar *archivo = NULL;
    gchar *fecha = NULL;
    gtk_tree_model_get(modelo, &iter, COL_HIST_ARCHIVO, &archivo, COL_HIST_FECHA, &fecha, -1);

    GtkWidget *confirmar = gtk_message_dialog_new(GTK_WINDOW(ctx->ventana),
        GTK_DIALOG_MODAL, GTK_MESSAGE_WARNING, GTK_BUTTONS_YES_NO,
        "Esto va a REEMPLAZAR la base de datos actual con el respaldo del\n%s (%s).\n\n"
        "Se guarda una copia de la base de datos actual antes de sobreescribir,\n"
        "por si acaso. ¿Continuar?",
        fecha ? fecha : "?", archivo ? archivo : "?");
    int respuesta = gtk_dialog_run(GTK_DIALOG(confirmar));
    gtk_widget_destroy(confirmar);

    if (respuesta != GTK_RESPONSE_YES || !archivo) {
        g_free(archivo);
        g_free(fecha);
        return;
    }
    g_free(fecha);

    gtk_widget_set_sensitive(ctx->btn_restaurar, FALSE);

    TareaRestaurar *t = g_new0(TareaRestaurar, 1);
    t->ctx = ctx;
    t->vivo = ctx->vivo;
    t->archivo = g_strdup(archivo);
    g_free(archivo);
    g_thread_new("pawos-restaurar-nube", hilo_restaurar_respaldo, t);
}

/* "Respaldar ahora" tambien habla con Google Drive (sube el archivo),
 * asi que corre en un hilo aparte por la misma razon que listar y
 * restaurar: para no congelar la ventana (y que el gestor de ventanas
 * no la marque como "no responde") mientras dura la subida.
 *
 * Antes esto se disparaba con "systemctl --no-block start
 * pawos-backup.service" (encola la tarea y regresa al instante, sin
 * esperar el resultado real). Ahora que ya existe el hilo en segundo
 * plano, se llama directo a pawos-backup-nube (via sudo -n, agregado a
 * sudoers) en ese hilo: espera el resultado real sin bloquear la GUI, y
 * de paso permite mandarle la etiqueta opcional que haya escrito el
 * usuario. */
typedef struct {
    ContextoRespaldo *ctx;
    gboolean         *vivo;
    char             *etiqueta;
    GtkWidget        *boton;
    int               rc;
} TareaRespaldar;

static gboolean aplicar_respaldar_ui(gpointer datos) {
    TareaRespaldar *t = (TareaRespaldar *)datos;

    if (*t->vivo) {
        ContextoRespaldo *ctx = t->ctx;
        gtk_widget_set_sensitive(t->boton, TRUE);

        if (t->rc == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Respaldo completado.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "No se pudo completar el respaldo.\n"
                "Verifica el permiso sudo (NOPASSWD) para\n"
                "'pawos-backup-nube' (ver README.md).", TRUE);
        }
        actualizar_estado_respaldo(ctx);
        cargar_historial_respaldos(ctx);
    }

    g_free(t->etiqueta);
    g_free(t);
    return G_SOURCE_REMOVE;
}

static gpointer hilo_respaldar_ahora(gpointer datos) {
    TareaRespaldar *t = (TareaRespaldar *)datos;

    char comando[300];
    snprintf(comando, sizeof(comando), "sudo -n /usr/local/bin/pawos-backup-nube '%s'", t->etiqueta);
    t->rc = system(comando);

    g_idle_add(aplicar_respaldar_ui, t);
    return NULL;
}

static void on_respaldar_ahora_clicked(GtkButton *boton, gpointer datos) {
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;

    if (ctx->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Requiere rol Administrador.", TRUE);
        return;
    }

    /* Etiqueta opcional, para poder reconocer este respaldo despues en
     * la tabla de historial (por ejemplo "antes-de-prueba") en vez de
     * solo por fecha. Se puede dejar vacio sin problema. */
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Respaldar ahora", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Respaldar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    GtkWidget *lbl = gtk_label_new("Nombre/etiqueta para este respaldo (opcional):");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entrada), "ej. antes-de-prueba (deja vacio si no quieres una)");
    gtk_entry_set_max_length(GTK_ENTRY(entrada), 40);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    /* Precargada con la etiqueta por defecto guardada, si hay una - se
     * puede borrar o cambiar aqui mismo, solo para este respaldo. */
    gtk_entry_set_text(GTK_ENTRY(entrada), gtk_entry_get_text(GTK_ENTRY(ctx->entrada_etiqueta_auto)));

    gtk_box_pack_start(GTK_BOX(caja), lbl, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), entrada, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);

    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    int respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    char etiqueta_buf[64] = "";
    if (respuesta == GTK_RESPONSE_OK) {
        snprintf(etiqueta_buf, sizeof(etiqueta_buf), "%s", gtk_entry_get_text(GTK_ENTRY(entrada)));
    }
    gtk_widget_destroy(dialogo);
    if (respuesta != GTK_RESPONSE_OK) return;

    gtk_widget_set_sensitive(GTK_WIDGET(boton), FALSE);

    TareaRespaldar *t = g_new0(TareaRespaldar, 1);
    t->ctx = ctx;
    t->vivo = ctx->vivo;
    t->etiqueta = g_strdup(etiqueta_buf);
    t->boton = GTK_WIDGET(boton);
    g_thread_new("pawos-backup-nube", hilo_respaldar_ahora, t);
}

/* Como liberar_contexto(), pero ademas marca ctx->vivo en FALSE antes
 * de liberar el contexto: los hilos en segundo plano (listar/restaurar/
 * respaldar) revisan esa bandera antes de tocar cualquier widget, por
 * si la ventana se cierra mientras una operacion de red sigue en
 * curso. La bandera en si (un solo gboolean) nunca se libera a
 * proposito, para que siga siendo valida aunque el hilo termine
 * despues de que ctx ya no exista. */
static void liberar_contexto_respaldo(GtkWidget *widget, gpointer datos) {
    (void)widget;
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;
    if (ctx->vivo) *ctx->vivo = FALSE;
    g_free(ctx);
}

static void abrir_pantalla_respaldo(GtkWidget *padre, Rol rol) {
    ContextoRespaldo *ctx = g_malloc0(sizeof(ContextoRespaldo));
    ctx->rol = rol;
    ctx->vivo = g_new(gboolean, 1);
    *ctx->vivo = TRUE;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Respaldo en la Nube");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 580, 700);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 16);

    /* caja_raiz separa el contenido (que puede crecer, por eso va
     * dentro de un GtkScrolledWindow) de la fila de botones de abajo
     * (Actualizar/Respaldar/Cerrar), que se queda siempre fija y
     * visible sin importar cuanto contenido haya arriba o que tan
     * chica quede la ventana. Antes todo iba en una sola caja sin
     * scroll, y al agregar la etiqueta por defecto el contenido crecio
     * lo suficiente para que los botones de abajo quedaran fuera del
     * area visible en ventanas mas chicas. */
    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    GtkWidget *scroll_principal = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_principal),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_principal, TRUE, TRUE, 0);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(scroll_principal), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Respaldo en la Nube</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "La base de datos del refugio se respalda automaticamente hacia Google Drive\n"
        "todas las noches (rclone + temporizador de systemd). Aqui puedes ver el\n"
        "estado de ese respaldo o dispararlo manualmente antes de tiempo.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *marco = gtk_frame_new("Estado actual");
    GtkWidget *caja_marco = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_marco), 10);
    gtk_container_add(GTK_CONTAINER(marco), caja_marco);

    ctx->lbl_ultimo = gtk_label_new("Ultimo respaldo automatico: -");
    ctx->lbl_estado = gtk_label_new("Estado del servicio: -");
    gtk_widget_set_halign(ctx->lbl_ultimo, GTK_ALIGN_START);
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_label_set_line_wrap(GTK_LABEL(ctx->lbl_ultimo), TRUE);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_ultimo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), marco, FALSE, FALSE, 0);

    /* --- Configuracion: Automatico (con intervalo) o Manual --- */
    GtkWidget *marco_config = gtk_frame_new("Configuracion del respaldo");
    GtkWidget *caja_config = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_config), 10);
    gtk_container_add(GTK_CONTAINER(marco_config), caja_config);

    ctx->lbl_modo = gtk_label_new("Modo actual: -");
    gtk_widget_set_halign(ctx->lbl_modo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->lbl_modo, FALSE, FALSE, 0);

    ctx->radio_auto = gtk_radio_button_new_with_label(NULL, "Automatico");
    ctx->radio_manual = gtk_radio_button_new_with_label_from_widget(
        GTK_RADIO_BUTTON(ctx->radio_auto), "Manual (solo con 'Respaldar ahora')");
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_auto, FALSE, FALSE, 0);

    ctx->combo_intervalo = gtk_combo_box_text_new();
    for (int i = 0; i < N_INTERVALOS; i++) {
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(ctx->combo_intervalo), INTERVALOS_ETIQUETA[i]);
    }
    gtk_combo_box_set_active(GTK_COMBO_BOX(ctx->combo_intervalo), 0);
    gtk_widget_set_margin_start(ctx->combo_intervalo, 24);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->combo_intervalo, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_manual, FALSE, FALSE, 0);

    GtkWidget *lbl_etiqueta_auto = gtk_label_new(
        "Etiqueta por defecto (opcional, se usa si 'Respaldar ahora' se deja\n"
        "en blanco, y tambien en el respaldo automatico):");
    gtk_widget_set_halign(lbl_etiqueta_auto, GTK_ALIGN_START);
    gtk_widget_set_margin_top(lbl_etiqueta_auto, 6);
    gtk_box_pack_start(GTK_BOX(caja_config), lbl_etiqueta_auto, FALSE, FALSE, 0);

    ctx->entrada_etiqueta_auto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ctx->entrada_etiqueta_auto),
        "ej. refugio-principal (deja vacio para no usar ninguna)");
    gtk_entry_set_max_length(GTK_ENTRY(ctx->entrada_etiqueta_auto), 40);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->entrada_etiqueta_auto, FALSE, FALSE, 0);

    GtkWidget *btn_guardar_config = gtk_button_new_with_label("Guardar configuracion");
    gtk_widget_set_halign(btn_guardar_config, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), btn_guardar_config, FALSE, FALSE, 4);

    gtk_box_pack_start(GTK_BOX(caja), marco_config, FALSE, FALSE, 0);

    /* --- Historial de respaldos: registro de lo que ya hay guardado en
     * Google Drive, por si hay que recuperar la base de datos despues
     * de un borrado accidental. --- */
    GtkWidget *marco_historial = gtk_frame_new("Historial de respaldos (Google Drive)");
    GtkWidget *caja_historial = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_historial), 10);
    gtk_container_add(GTK_CONTAINER(marco_historial), caja_historial);

    GtkWidget *lbl_historial = gtk_label_new(
        "Cada respaldo queda guardado por separado (no se pisan entre si).\n"
        "Al usar 'Respaldar ahora' puedes ponerle una etiqueta para reconocerlo\n"
        "despues. Selecciona uno y usa 'Restaurar seleccionado' para recuperarlo.");
    gtk_label_set_justify(GTK_LABEL(lbl_historial), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), lbl_historial, FALSE, FALSE, 0);

    ctx->modelo_historial = gtk_list_store_new(N_COL_HIST,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->lista_historial = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->modelo_historial));

    GtkCellRenderer *render_fecha = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Fecha del respaldo", render_fecha, "text", COL_HIST_FECHA, NULL);
    GtkCellRenderer *render_etiqueta = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Etiqueta", render_etiqueta, "text", COL_HIST_ETIQUETA, NULL);
    GtkCellRenderer *render_tamano = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Tamano (bytes)", render_tamano, "text", COL_HIST_TAMANO, NULL);

    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 140);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->lista_historial);
    gtk_box_pack_start(GTK_BOX(caja_historial), scroll_historial, TRUE, TRUE, 0);

    ctx->btn_restaurar = gtk_button_new_with_label("Restaurar seleccionado");
    gtk_widget_set_halign(ctx->btn_restaurar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), ctx->btn_restaurar, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja), marco_historial, TRUE, TRUE, 0);

    /* Fuera del scroll a proposito (ver comentario en caja_raiz, arriba):
     * estos botones siempre tienen que estar visibles. */
    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja_raiz), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar estado");
    GtkWidget *btn_respaldar  = gtk_button_new_with_label("Respaldar ahora");
    GtkWidget *btn_cerrar     = gtk_button_new_with_label("Cerrar");
    ctx->btn_actualizar = btn_actualizar;

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_respaldar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que Procesos/Memoria: se muestra siempre, solo se
     * deshabilita para quien no sea Administrador. */
    if (rol != ROL_ADMIN) {
        gtk_widget_set_sensitive(btn_respaldar, FALSE);
        gtk_widget_set_tooltip_text(btn_respaldar, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->radio_auto, FALSE);
        gtk_widget_set_sensitive(ctx->radio_manual, FALSE);
        gtk_widget_set_sensitive(ctx->combo_intervalo, FALSE);
        gtk_widget_set_sensitive(ctx->entrada_etiqueta_auto, FALSE);
        gtk_widget_set_sensitive(btn_guardar_config, FALSE);
        gtk_widget_set_tooltip_text(btn_guardar_config, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->btn_restaurar, FALSE);
        gtk_widget_set_tooltip_text(ctx->btn_restaurar, "Requiere rol Administrador.");
    }

    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_estado_respaldo_clicked), ctx);
    g_signal_connect(btn_respaldar, "clicked", G_CALLBACK(on_respaldar_ahora_clicked), ctx);
    g_signal_connect(ctx->radio_auto, "toggled", G_CALLBACK(on_radio_modo_respaldo_toggled), ctx);
    g_signal_connect(btn_guardar_config, "clicked", G_CALLBACK(on_guardar_config_respaldo_clicked), ctx);
    g_signal_connect(ctx->btn_restaurar, "clicked", G_CALLBACK(on_restaurar_respaldo_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto_respaldo), ctx);

    actualizar_estado_respaldo(ctx);
    actualizar_ui_modo_respaldo(ctx);
    cargar_historial_respaldos(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Alertas de Sensores (ESP32)
 *
 * Guarda y muestra las alertas de posible lesion, hambre, sed o
 * maltrato que detecta el ESP32. Tipos contemplados:
 *   - temperatura:             fiebre o hipotermia (MLX90614)
 *   - movimiento:               golpe/impacto brusco (MPU6050)
 *   - inactividad:              el animal no se mueve por mucho tiempo (dolor)
 *   - sonido:                   gemidos o llanto sostenido
 *   - sin_comer:                no se detecto consumo en el comedero por
 *                                mas de X horas (a futuro: sensor de peso
 *                                tipo celda de carga HX711, o sensor de
 *                                barrera IR en el comedero)
 *   - sin_beber_agua:           mismo caso pero en el bebedero
 *   - aislamiento_prolongado:   el animal no se acerca a su zona social
 *                                habitual por mucho tiempo
 *   - combinada:                dos o mas senales activas a la vez
 *                                (prioridad alta)
 * Por ahora no hay un puente que reciba las peticiones HTTP del ESP32
 * y llame a alerta_registrar() automaticamente (eso queda pendiente,
 * junto con el sensor de comedero/bebedero, para cuando retomemos el
 * ESP32); mientras tanto, este modulo incluye un boton para registrar
 * una alerta de prueba y validar que todo el flujo (guardar, listar,
 * marcar como atendida) funciona.
 * ================================================================= */

enum {
    COL_AL_ID = 0,
    COL_AL_ANIMAL,
    COL_AL_TIPO,
    COL_AL_DETALLE,
    COL_AL_VALOR,
    COL_AL_FECHA,
    COL_AL_ATENDIDA,
    N_COL_ALERTAS
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *treeview;
    GtkListStore *store;
    Rol           rol;
    gboolean      solo_pendientes;
} ContextoAlertas;

static void cargar_alertas(ContextoAlertas *ctx) {
    gtk_list_store_clear(ctx->store);

    Alerta *als;
    int n;
    int rc = ctx->solo_pendientes ? alerta_pendientes(&als, &n) : alerta_listar(&als, &n);
    if (rc != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de alertas.", TRUE);
        return;
    }

    for (int i = 0; i < n; i++) {
        char valor_txt[32];
        snprintf(valor_txt, sizeof(valor_txt), "%.2f", als[i].valor);

        GtkTreeIter iter;
        gtk_list_store_append(ctx->store, &iter);
        gtk_list_store_set(ctx->store, &iter,
            COL_AL_ID, als[i].id,
            COL_AL_ANIMAL, als[i].animal_id,
            COL_AL_TIPO, als[i].tipo,
            COL_AL_DETALLE, als[i].detalle,
            COL_AL_VALOR, valor_txt,
            COL_AL_FECHA, als[i].fecha_hora,
            COL_AL_ATENDIDA, als[i].atendida ? "Si" : "Pendiente",
            -1);
    }
    free(als);
}

static void on_ver_todas_alertas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAlertas *ctx = (ContextoAlertas *)datos;
    ctx->solo_pendientes = FALSE;
    cargar_alertas(ctx);
}

static void on_ver_pendientes_alertas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAlertas *ctx = (ContextoAlertas *)datos;
    ctx->solo_pendientes = TRUE;
    cargar_alertas(ctx);
}

static void on_marcar_atendida_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAlertas *ctx = (ContextoAlertas *)datos;

    int id;
    if (!obtener_id_seleccionado(ctx->treeview, COL_AL_ID, &id)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una alerta de la lista.", TRUE);
        return;
    }

    if (alerta_marcar_atendida(id) == 0) {
        cargar_alertas(ctx);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Alerta marcada como atendida.", FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar la alerta.", TRUE);
    }
}

static void on_registrar_alerta_prueba_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoAlertas *ctx = (ContextoAlertas *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrar alerta de prueba", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 8);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 10);
    gtk_container_set_border_width(GTK_CONTAINER(cuadricula), 12);

    GtkWidget *e_animal = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_animal), "MASCOTA-001");

    GtkWidget *combo_tipo = gtk_combo_box_text_new();
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "temperatura");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "movimiento");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "inactividad");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "sonido");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "sin_comer");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "sin_beber_agua");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "aislamiento_prolongado");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo_tipo), "combinada");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo_tipo), 0);

    GtkWidget *e_detalle = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_detalle), "Posible fiebre o infeccion");

    GtkWidget *e_valor = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_valor), "39.8");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("ID del animal:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_animal, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Tipo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), combo_tipo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Detalle:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_detalle, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Valor:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_valor, 1, 3, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Alerta a;
        memset(&a, 0, sizeof(a));
        snprintf(a.animal_id, sizeof(a.animal_id), "%s", gtk_entry_get_text(GTK_ENTRY(e_animal)));
        gchar *tipo = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(combo_tipo));
        snprintf(a.tipo, sizeof(a.tipo), "%s", tipo ? tipo : "combinada");
        g_free(tipo);
        snprintf(a.detalle, sizeof(a.detalle), "%s", gtk_entry_get_text(GTK_ENTRY(e_detalle)));
        a.valor = atof(gtk_entry_get_text(GTK_ENTRY(e_valor)));

        if (strlen(a.animal_id) == 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "El ID del animal es obligatorio.", TRUE);
        } else if (alerta_registrar(&a) == 0) {
            cargar_alertas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Alerta de prueba registrada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la alerta.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void abrir_pantalla_alertas(GtkWidget *padre, Rol rol) {
    ContextoAlertas *ctx = g_malloc0(sizeof(ContextoAlertas));
    ctx->rol = rol;
    ctx->solo_pendientes = TRUE;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Alertas de Sensores");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 760, 480);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Alertas de Sensores (ESP32)</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new(
        "Posibles senales de lesion, fiebre o maltrato detectadas por los sensores del collar.");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_ALERTAS,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_ALERTAS] = {"ID", "Animal", "Tipo", "Detalle", "Valor", "Fecha/hora", "Atendida"};
    for (int i = 0; i < N_COL_ALERTAS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_pendientes = gtk_button_new_with_label("Ver pendientes");
    GtkWidget *btn_todas      = gtk_button_new_with_label("Ver todas");
    GtkWidget *btn_atendida   = gtk_button_new_with_label("Marcar como atendida");
    GtkWidget *btn_prueba     = gtk_button_new_with_label("Registrar alerta de prueba");
    GtkWidget *btn_cerrar     = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_pendientes, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_todas, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_atendida, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_prueba, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Ver alertas: todos los roles (es informacion de bienestar animal).
     * Marcar como atendida / registrar de prueba: solo Admin y
     * Veterinario, igual que Vacunas. */
    if (rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(btn_atendida, FALSE);
        gtk_widget_set_sensitive(btn_prueba, FALSE);
        gtk_widget_set_tooltip_text(btn_atendida, "Requiere rol Admin o Veterinario.");
        gtk_widget_set_tooltip_text(btn_prueba, "Requiere rol Admin o Veterinario.");
    }

    g_signal_connect(btn_pendientes, "clicked", G_CALLBACK(on_ver_pendientes_alertas_clicked), ctx);
    g_signal_connect(btn_todas, "clicked", G_CALLBACK(on_ver_todas_alertas_clicked), ctx);
    g_signal_connect(btn_atendida, "clicked", G_CALLBACK(on_marcar_atendida_clicked), ctx);
    g_signal_connect(btn_prueba, "clicked", G_CALLBACK(on_registrar_alerta_prueba_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_alertas(ctx);
    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Ventana principal
 * ================================================================= */

typedef struct {
    GtkWidget  *ventana_principal;
    Rol         rol;
    const char *usuario;
} DatosBotonModulo;

static void on_mascotas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_mascotas(d->ventana_principal, d->rol);
}

static void on_vacunas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_vacunas(d->ventana_principal, d->rol);
}

static void on_adopciones_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_adopciones(d->ventana_principal, d->rol);
}

/* Donantes: informacion sensible -> solo Admin y Veterinario, no Voluntario
 * (igual que pantalla_donantes() en pantallas.c) */
static void on_donantes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol == ROL_VOLUNTARIO) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso restringido: este modulo requiere rol Admin o Veterinario.", TRUE);
        return;
    }
    abrir_pantalla_donantes(d->ventana_principal, d->rol);
}

/* Reportes: igual que pantalla_reportes() en pantallas.c */
static void on_reportes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol == ROL_VOLUNTARIO) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso restringido: este modulo requiere rol Admin o Veterinario.", TRUE);
        return;
    }
    abrir_pantalla_reportes(d->ventana_principal, d->rol);
}

/* Procesos: solo Administrador, igual que pantalla_procesos() */
static void on_procesos_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso denegado: esta seccion es solo para el Administrador.", TRUE);
        return;
    }
    abrir_pantalla_procesos(d->ventana_principal);
}

/* Memoria: solo Administrador, igual que pantalla_memoria() */
static void on_memoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso denegado: esta seccion es solo para el Administrador.", TRUE);
        return;
    }
    abrir_pantalla_memoria(d->ventana_principal);
}

/* Respaldo en la Nube: la ventana se abre para cualquier rol (ver el
 * estado es solo lectura); el boton "Respaldar ahora" de adentro es el
 * que queda deshabilitado si el rol no es Administrador. */
static void on_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_respaldo(d->ventana_principal, d->rol);
}

/* Alertas de Sensores: la ventana se abre para cualquier rol (ver
 * alertas es informacion de bienestar animal); "Marcar como atendida"
 * y "Registrar alerta de prueba" quedan deshabilitados para Voluntario
 * dentro de la propia ventana. */
static void on_alertas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_alertas(d->ventana_principal, d->rol);
}

/* Clasifica cada linea del changelog con un icono, al estilo de las
 * notas de version de Google Play / Windows Update (novedad, mejora,
 * correccion de estabilidad). Heuristica simple por palabras clave,
 * solo cosmetica -- no cambia el contenido del mensaje. */
static const char *clasificar_commit_icono(const char *mensaje) {
    gchar *minuscula = g_utf8_strdown(mensaje, -1);
    const char *icono;
    if (strstr(minuscula, "arregla") || strstr(minuscula, "corrige") ||
        strstr(minuscula, "arreglo") || strstr(minuscula, "error") ||
        strstr(minuscula, "bug") || strstr(minuscula, "fix")) {
        icono = "\xF0\x9F\x94\xA7"; /* llave inglesa = estabilidad */
    } else if (strstr(minuscula, "mejora") || strstr(minuscula, "optimiza") ||
               strstr(minuscula, "profesional") || strstr(minuscula, "diseno") ||
               strstr(minuscula, "dise\xC3\xB1o")) {
        icono = "\xE2\xAD\x90"; /* estrella = mejora */
    } else {
        icono = "\xE2\x9C\xA8"; /* destellos = novedad */
    }
    g_free(minuscula);
    return icono;
}

static void on_actualizar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;

    GtkWidget *dialogo_buscando = gtk_message_dialog_new(
        padre, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_NONE,
        "Buscando actualizaciones...");
    gtk_widget_show_all(dialogo_buscando);
    while (gtk_events_pending()) gtk_main_iteration();

    gchar *salida = NULL;
    gchar *error_salida = NULL;
    gint estado_salida = 0;
    GError *error = NULL;
    const gchar *comando =
        "bash -c '"
        "REPO_DIR=/opt/pawos-src; RAMA=rama-Kevin; "
        "git config --global --add safe.directory \"$REPO_DIR\" 2>/dev/null; "
        "if [ -d \"$REPO_DIR/.git\" ]; then "
        "  cd \"$REPO_DIR\" || { echo SIN_CONEXION; exit 0; }; "
        "  git fetch origin \"$RAMA\" >/dev/null 2>&1 || { echo SIN_CONEXION; exit 0; }; "
        "  LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse origin/$RAMA); "
        "  if [ \"$LOCAL\" = \"$REMOTE\" ]; then echo AL_DIA; "
        "  else echo HAY_CAMBIOS; git log \"$LOCAL..$REMOTE\" --no-merges --pretty=format:%s; fi; "
        "else echo PRIMERA_VEZ; fi'";

    gboolean ok = g_spawn_command_line_sync(comando, &salida, &error_salida, &estado_salida, &error);
    gtk_widget_destroy(dialogo_buscando);
    g_free(error_salida);

    if (!ok) {
        mostrar_mensaje(padre, "No se pudo buscar actualizaciones. Revisa tu conexion a internet.", TRUE);
        if (error) g_error_free(error);
        g_free(salida);
        return;
    }

    gchar **lineas = g_strsplit(salida ? salida : "", "\n", -1);
    g_free(salida);
    const char *estado = lineas[0] ? lineas[0] : "";

    if (g_strcmp0(estado, "SIN_CONEXION") == 0) {
        mostrar_mensaje(padre, "No se pudo conectar para buscar actualizaciones.\nRevisa tu conexion a internet.", TRUE);
        g_strfreev(lineas);
        return;
    }
    if (g_strcmp0(estado, "AL_DIA") == 0) {
        mostrar_mensaje(padre, "Ya tienes la ultima version instalada.", FALSE);
        g_strfreev(lineas);
        return;
    }

    /* HAY_CAMBIOS o PRIMERA_VEZ: mostramos el dialogo de novedades,
     * al estilo de una tienda de aplicaciones. */
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS - Actualizaciones", padre, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Actualizar ahora", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 460, 420);

    GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area_contenido), 16);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(area_contenido), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    if (g_strcmp0(estado, "PRIMERA_VEZ") == 0) {
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\xF0\x9F\x93\xA5 Version disponible para instalar</span>");
    } else {
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\xF0\x9F\x94\x84 Nueva version disponible</span>");
    }
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new(
        g_strcmp0(estado, "PRIMERA_VEZ") == 0
            ? "Se instalara PawOS Refugio por primera vez en este equipo."
            : "Novedades, mejoras y correcciones de esta actualizacion:");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_label_set_line_wrap(GTK_LABEL(subtitulo), TRUE);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *lista_novedades = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_container_add(GTK_CONTAINER(scroll), lista_novedades);

    int total_items = 0;
    for (int i = 1; lineas[i] != NULL && total_items < 40; i++) {
        if (lineas[i][0] == '\0') continue;
        const char *icono = clasificar_commit_icono(lineas[i]);
        gchar *texto_item = g_strdup_printf("%s  %s", icono, lineas[i]);
        GtkWidget *lbl_item = gtk_label_new(texto_item);
        g_free(texto_item);
        gtk_label_set_line_wrap(GTK_LABEL(lbl_item), TRUE);
        gtk_widget_set_halign(lbl_item, GTK_ALIGN_START);
        gtk_box_pack_start(GTK_BOX(lista_novedades), lbl_item, FALSE, FALSE, 0);
        total_items++;
    }
    if (total_items == 0) {
        GtkWidget *lbl_vacio = gtk_label_new("(Sin detalle de cambios disponible)");
        gtk_box_pack_start(GTK_BOX(lista_novedades), lbl_vacio, FALSE, FALSE, 0);
    }
    g_strfreev(lineas);

    gtk_widget_show_all(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == GTK_RESPONSE_ACCEPT) {
        GError *error_terminal = NULL;
        gboolean ok_terminal = g_spawn_command_line_async(
            "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error_terminal);
        if (!ok_terminal) {
            g_warning("No se pudo abrir el actualizador: %s", error_terminal ? error_terminal->message : "error desconocido");
            if (error_terminal) g_error_free(error_terminal);
        }
    }
}

/* ---------------- Administrar Colaboradores (solo Admin) ---------------- */

static const char *nombre_rol_colaborador(int rol) {
    switch (rol) {
        case ROL_ADMIN: return "Administrador";
        case ROL_VETERINARIO: return "Veterinario";
        case ROL_RESCATISTA: return "Rescatista";
        case ROL_RECEPCIONISTA: return "Recepcionista";
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
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "3", "Rescatista");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo_rol), "4", "Recepcionista");
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

        if (usuario[0] == '\0' || strlen(pass) < 4) {
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
    /* g_signal_connect_swapped (no g_signal_connect normal): asi GTK
     * llama g_free(ctx) directo. Con g_signal_connect normal el
     * callback recibe (ventana, ctx) y terminaria intentando liberar
     * la ventana misma con g_free(), lo cual corrompe la memoria. */
    g_signal_connect_swapped(ventana, "destroy", G_CALLBACK(g_free), ctx);

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

/* Dice si el rol dado tiene acceso al modulo "indice" (mismo orden
 * que nombres_modulos[] mas abajo):
 *   0=Mascotas 1=Vacunas 2=Adopciones 3=Donantes 4=Reportes
 *   5=Procesos 6=Memoria 7=Respaldo 8=Alertas 9=AdministrarColaboradores
 * Administrador siempre tiene acceso a todo. Veterinario y Voluntario
 * mantienen las mismas reglas de antes; Rescatista y Recepcionista
 * son roles mas acotados, pensados para tareas especificas. */
static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9 || indice == 10 || indice == 11);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9 || indice == 10 || indice == 11);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}

/* Cambia el rol (Jefe/Supervisor/Administrador) de un Cliente ya
 * registrado -- necesario porque el registro publico ya no deja
 * elegirlo (ver mostrar_registro_cliente). Solo Administrador. */
static void on_cambiar_rol_cliente_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkTreeView *vista = GTK_TREE_VIEW(datos);
    GtkTreeSelection *seleccion = gtk_tree_view_get_selection(vista);
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(seleccion, &modelo, &iter)) {
        mostrar_mensaje(NULL, "Selecciona un Cliente de la lista primero.", TRUE);
        return;
    }
    gint id_cliente;
    gtk_tree_model_get(modelo, &iter, 0, &id_cliente, -1);

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Cambiar rol", NULL, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *combo = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
    gtk_container_set_border_width(GTK_CONTAINER(combo), 12);
    gtk_container_add(GTK_CONTAINER(area), combo);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const gchar *id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(combo));
        RolCliente nuevo_rol = id_texto ? (RolCliente)atoi(id_texto) : ROL_CLIENTE_JEFE;
        if (cliente_actualizar_rol(id_cliente, nuevo_rol) == 0) {
            gtk_list_store_set(GTK_LIST_STORE(modelo), &iter, 2, cliente_rol_nombre(nuevo_rol), -1);
            mostrar_mensaje(NULL, "Rol actualizado.", FALSE);
        } else {
            mostrar_mensaje(NULL, "No se pudo actualizar el rol.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;
    if (!d || d->rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Solo el Administrador puede administrar Clientes.", TRUE);
        return;
    }

    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "Administrar Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 520, 400);
    gtk_window_set_transient_for(GTK_WINDOW(ventana), padre);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER_ON_PARENT);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    GtkListStore *store = gtk_list_store_new(4, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    Cliente *lista = NULL;
    int n = 0;
    cliente_listar(&lista, &n);
    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(store, &iter);
        gtk_list_store_set(store, &iter,
            0, lista[i].id,
            1, lista[i].nombre,
            2, cliente_rol_nombre(lista[i].rol),
            3, lista[i].correo,
            -1);
    }
    free(lista);

    GtkWidget *vista = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    g_object_unref(store);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Nombre", gtk_cell_renderer_text_new(), "text", 1, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Rol actual", gtk_cell_renderer_text_new(), "text", 2, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Correo", gtk_cell_renderer_text_new(), "text", 3, NULL);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll), vista);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *btn_cambiar = gtk_button_new_with_label("Cambiar rol del seleccionado");
    g_signal_connect(btn_cambiar, "clicked", G_CALLBACK(on_cambiar_rol_cliente_clicked), vista);
    gtk_box_pack_start(GTK_BOX(caja), btn_cambiar, FALSE, FALSE, 0);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    gtk_widget_show_all(ventana);
}

/* Pantalla de Administrador para guardar las credenciales de correo
 * (Gmail) y WhatsApp (Green API) usadas por Agenda de Vacunas para
 * mandar recordatorios de citas. El formulario mismo NO escribe el
 * archivo de configuracion -- solo llama (via sudo) al script
 * pawos-configurar-notificaciones, el unico con permiso de escribir
 * /etc/pawos/notificaciones.conf (protegido, 600, root:root). */
static void on_configurar_notificaciones_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;
    if (!d || d->rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Solo el Administrador puede configurar las notificaciones.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Configurar Notificaciones", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 420, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 14);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *aviso = gtk_label_new(
        "Credenciales para mandar recordatorios de citas por correo y WhatsApp.\n"
        "Se guardan protegidas en el sistema (no se muestran de vuelta).");
    gtk_label_set_line_wrap(GTK_LABEL(aviso), TRUE);
    gtk_grid_attach(GTK_GRID(grid), aviso, 0, 0, 2, 1);

    GtkWidget *e_gmail_user = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_user), "correo@gmail.com");
    GtkWidget *e_gmail_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_gmail_pass), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_pass), "Contrasena de aplicacion (16 caracteres)");
    GtkWidget *e_green_url = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_url), "https://XXXX.api.greenapi.com");
    GtkWidget *e_green_id = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_id), "idInstance");
    GtkWidget *e_green_token = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_green_token), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_token), "apiTokenInstance");

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo Gmail:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_gmail_user, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena de app:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_gmail_pass, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API URL:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_url, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API idInstance:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_id, 1, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API apiToken:"), 0, 5, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_token, 1, 5, 1, 1);

    gtk_widget_show_all(dialogo);
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const char *gmail_user = gtk_entry_get_text(GTK_ENTRY(e_gmail_user));
        const char *gmail_pass = gtk_entry_get_text(GTK_ENTRY(e_gmail_pass));
        const char *green_url = gtk_entry_get_text(GTK_ENTRY(e_green_url));
        const char *green_id = gtk_entry_get_text(GTK_ENTRY(e_green_id));
        const char *green_token = gtk_entry_get_text(GTK_ENTRY(e_green_token));

        if (!gmail_user[0] || !gmail_pass[0] || !green_url[0] || !green_id[0] || !green_token[0]) {
            mostrar_mensaje(padre, "Completa todos los campos.", TRUE);
        } else {
            FILE *proceso = popen("sudo /usr/local/bin/pawos-configurar-notificaciones", "w");
            if (!proceso) {
                mostrar_mensaje(padre, "No se pudo iniciar el guardado de la configuracion.", TRUE);
            } else {
                fprintf(proceso, "%s\n%s\n%s\n%s\n%s\n", gmail_user, gmail_pass, green_url, green_id, green_token);
                int rc = pclose(proceso);
                if (rc == 0) {
                    mostrar_mensaje(padre, "Configuracion guardada correctamente.", FALSE);
                } else {
                    mostrar_mensaje(padre, "No se pudo guardar la configuracion (revisa permisos de sudo).", TRUE);
                }
            }
        }
    }
    gtk_widget_destroy(dialogo);
}

static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 580, 660);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    /* Banner de encabezado: titulo + insignia de rol con color propio,
     * en vez de una simple etiqueta de texto plano. */
    GtkWidget *banner = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(banner), "encabezado-banner");
    gtk_box_pack_start(GTK_BOX(caja), banner, FALSE, FALSE, 0);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_version = gtk_label_new(NULL);
    gchar *markup_version = g_strdup_printf("<span size='small'>v%s</span>", PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_version), markup_version);
    g_free(markup_version);
    gtk_widget_set_halign(lbl_version, GTK_ALIGN_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_version), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(banner), lbl_version, FALSE, FALSE, 0);

    GtkWidget *fila_usuario = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_widget_set_halign(fila_usuario, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(banner), fila_usuario, FALSE, FALSE, 0);

    GtkWidget *lbl_bienvenida = gtk_label_new(NULL);
    gchar *texto_bienvenida = g_strdup_printf("Bienvenido, %s", usuario);
    gtk_label_set_text(GTK_LABEL(lbl_bienvenida), texto_bienvenida);
    g_free(texto_bienvenida);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_bienvenida), "subtitulo-banner");
    gtk_box_pack_start(GTK_BOX(fila_usuario), lbl_bienvenida, FALSE, FALSE, 0);

    GtkWidget *badge_rol = gtk_label_new(auth_rol_nombre(rol));
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), "badge");
    const char *clase_badge =
        (rol == ROL_ADMIN)         ? "badge-admin" :
        (rol == ROL_VETERINARIO)   ? "badge-veterinario" :
        (rol == ROL_RESCATISTA)    ? "badge-rescatista" :
        (rol == ROL_RECEPCIONISTA) ? "badge-recepcionista" : "badge-voluntario";
    gtk_style_context_add_class(gtk_widget_get_style_context(badge_rol), clase_badge);
    gtk_box_pack_start(GTK_BOX(fila_usuario), badge_rol, FALSE, FALSE, 0);

    GtkWidget *cuadricula = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuadricula), 12);
    gtk_grid_set_column_spacing(GTK_GRID(cuadricula), 12);
    gtk_grid_set_column_homogeneous(GTK_GRID(cuadricula), TRUE);
    gtk_widget_set_vexpand(cuadricula, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), cuadricula, TRUE, TRUE, 0);

    const char *nombres_modulos[] = {
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
        "Configurar Notificaciones",
        "Administrar Clientes",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\xF0\x9F\x90\xBE", /* paw */
        "\xF0\x9F\x92\x89", /* syringe */
        "\xF0\x9F\x8F\xA0", /* house */
        "\xF0\x9F\x92\xB0", /* money bag */
        "\xF0\x9F\x93\x8A", /* bar chart */
        "\xE2\x9A\x99",     /* gear */
        "\xF0\x9F\xA7\xA0", /* brain */
        "\xE2\x98\x81",     /* cloud */
        "\xF0\x9F\x9A\xA8", /* siren */
        "\xF0\x9F\x91\xA5", /* people */
        "\xF0\x9F\x93\xA7", /* envelope */
        "\xF0\x9F\x9B\x82", /* briefcase */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion", "cat-gestion",
    };
    GCallback manejadores[] = {
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
        G_CALLBACK(on_configurar_notificaciones_clicked),
        G_CALLBACK(on_administrar_clientes_clicked),
    };
    const int total_modulos = 12;

    DatosBotonModulo *datos_botones = g_malloc(sizeof(DatosBotonModulo));
    datos_botones->ventana_principal = ventana;
    datos_botones->rol = rol;
    datos_botones->usuario = usuario;
    g_signal_connect(ventana, "destroy", G_CALLBACK(liberar_contexto), datos_botones);

    for (int i = 0; i < total_modulos; i++) {
        gchar *etiqueta = g_strdup_printf("%s  %s", iconos_modulos[i], nombres_modulos[i]);
        GtkWidget *boton = gtk_button_new_with_label(etiqueta);
        g_free(etiqueta);
        gtk_widget_set_size_request(boton, 250, 58);
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), "modulo");
        gtk_style_context_add_class(gtk_widget_get_style_context(boton), categorias_modulos[i]);
        gtk_grid_attach(GTK_GRID(cuadricula), boton, i % 2, i / 2, 1, 1);
        g_signal_connect(boton, "clicked", manejadores[i], datos_botones);

        /* Los botones siempre se muestran; solo se deshabilitan (no se
         * ocultan) cuando el rol actual no tiene acceso a ese modulo,
         * igual que ya hacian las pantallas del CLI. */
        if (!modulo_permitido(rol, i)) {
            gtk_widget_set_sensitive(boton, FALSE);
            gtk_widget_set_tooltip_text(boton, "Tu rol no tiene acceso a este modulo.");
        }
    }

    GtkWidget *btn_actualizar = gtk_button_new_with_label("\xF0\x9F\x94\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, 250, 46);
    gtk_widget_set_halign(btn_actualizar, GTK_ALIGN_CENTER);
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(caja), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);

    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_salir), "salir");
    gtk_widget_set_size_request(btn_salir, 250, 46);
    gtk_widget_set_halign(btn_salir, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(caja), btn_salir, FALSE, FALSE, 0);
    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

    gtk_widget_show_all(ventana);
}

/* ---------------------------------------------------------------
 * main
 * --------------------------------------------------------------- */

/* =================================================================
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
    int           id_cliente;
    RolCliente    rol;
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

/* Ver mis solicitudes: solo Supervisor y Administrador (de Cliente).
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
    g_string_append(texto, "<b>Adopciones solicitadas:</b>\n");
    Adopcion *ads; int n_ads;
    if (adopcion_listar(&ads, &n_ads) == 0) {
        int encontradas = 0;
        for (int i = 0; i < n_ads; i++) {
            if (g_strcmp0(ads[i].adoptante_nombre, ctx->nombre_cliente) == 0) {
                gchar *linea = g_markup_printf_escaped(
                    "  - Mascota #%d, %s\n", ads[i].mascota_id, ads[i].fecha_adopcion);
                g_string_append(texto, linea);
                g_free(linea);
                encontradas++;
            }
        }
        if (encontradas == 0) g_string_append(texto, "  (ninguna todavia)\n");
        free(ads);
    }

    g_string_append(texto, "\n<b>Donaciones:</b>\n");
    Donante *ds; int n_ds;
    if (donante_listar(&ds, &n_ds) == 0) {
        int encontradas = 0;
        for (int i = 0; i < n_ds; i++) {
            if (g_strcmp0(ds[i].nombre, ctx->nombre_cliente) == 0) {
                gchar *linea = g_markup_printf_escaped(
                    "  - $%.2f, %s\n", ds[i].monto, ds[i].fecha);
                g_string_append(texto, linea);
                g_free(linea);
                encontradas++;
            }
        }
        if (encontradas == 0) g_string_append(texto, "  (ninguna todavia)\n");
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
        "<span size='large' weight='bold'>\xC2\xA1Hola, %s!</span> (%s)",
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
}

/* Formulario para crear una cuenta de Cliente nueva (correo, nombre,
 * contrasena), llamado desde el boton "Registrarme" del login de
 * clientes. Devuelve TRUE y llena nombre_out si se creo la cuenta. */
static gboolean mostrar_registro_cliente(Cliente *cliente_out) {
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

    GtkWidget *e_telefono = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(e_telefono), GTK_INPUT_PURPOSE_PHONE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_telefono), "Ej: 50412345678 (con codigo de pais)");

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Telefono (WhatsApp):"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_telefono, 1, 3, 1, 1);

    gtk_widget_show_all(dialogo);

    gboolean creado = FALSE;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *correo = gtk_entry_get_text(GTK_ENTRY(e_correo));
        const char *password = gtk_entry_get_text(GTK_ENTRY(e_password));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(e_telefono));
        /* Ya no se deja elegir el rol al registrarse: si cualquiera
         * pudiera auto-asignarse el nivel mas alto, nadie elegiria uno
         * mas bajo y la jerarquia no serviria de nada. Todo Cliente
         * nuevo entra en el nivel base; el Administrador del refugio
         * lo puede subir despues desde "Administrar Clientes". */
        RolCliente rol_elegido = ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, telefono, rol_elegido) == 0
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
}

/* Login de Clientes (correo/contrasena, tabla "clientes"). Si todavia
 * no tiene cuenta, el boton "Registrarme" la crea ahi mismo. Hasta 3
 * intentos fallidos (crear cuenta no cuenta como intento). Devuelve
 * TRUE y llena nombre_out si el login (o el registro) fue exitoso. */
static gboolean mostrar_login_cliente(Cliente *cliente_out, gboolean *es_admin_out) {
    int intentos = 0;
    const int max_intentos = 3;
    gboolean no_registrado = FALSE;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,
            "Regresar", GTK_RESPONSE_CANCEL,
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
            "<span size='large' weight='bold'>\xF0\x9F\x90\xBE Acceso de Clientes</span>");
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

        if (respuesta == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            if (mostrar_registro_cliente(cliente_out)) {
                mostrar_mensaje(NULL, "Cuenta creada. Bienvenido a PawOS.", FALSE);
                if (es_admin_out) *es_admin_out = FALSE;
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

        /* Acceso oculto para el Administrador: sin boton en ningun
         * lado, a proposito. Si lo que se escribio aqui coincide con
         * las credenciales REALES del Administrador (tabla "usuarios",
         * no "clientes"), se abre la ventana completa de Administrador
         * en vez de la de Cliente. */
        int rol_secreto = -1;
        if (usuario_autenticar(correo_ingresado, password_ingresado, &rol_secreto) == 0
            && rol_secreto == ROL_ADMIN) {
            /* Copiar el texto ANTES de destruir el dialogo: una vez
             * destruido, "correo_ingresado" (que apunta al buffer
             * interno del GtkEntry) queda invalido -- leerlo despues
             * es memoria ya liberada (use-after-free). */
            snprintf(cliente_out->nombre, sizeof(cliente_out->nombre), "%s", correo_ingresado);
            gtk_widget_destroy(dialogo);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
        }

        gboolean ok = (cliente_autenticar(correo_ingresado, password_ingresado, cliente_out) == 0);
        gtk_widget_destroy(dialogo);

        if (ok) {
            if (es_admin_out) *es_admin_out = FALSE;
            return TRUE;
        }
        no_registrado = !cliente_existe(correo_ingresado);
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
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new("\xC2\xBF" "Como quieres entrar?");
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
static gboolean mostrar_login_gtk(char *usuario_out, size_t usuario_len, Rol *rol_out) {
    int intentos = 0;
    const int max_intentos = 3;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Inicio de sesion", NULL, GTK_DIALOG_MODAL,
            "Regresar", GTK_RESPONSE_CANCEL,
            "Ingresar", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area_contenido), caja);

        GtkWidget *titulo = gtk_label_new(NULL);
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
        gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

        GtkWidget *grid = gtk_grid_new();
        gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
        gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
        gtk_box_pack_start(GTK_BOX(caja), grid, FALSE, FALSE, 0);

        GtkWidget *lbl_usuario = gtk_label_new("Usuario:");
        gtk_widget_set_halign(lbl_usuario, GTK_ALIGN_END);
        GtkWidget *entrada_usuario = gtk_entry_new();
        gtk_grid_attach(GTK_GRID(grid), lbl_usuario, 0, 0, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_usuario, 1, 0, 1, 1);

        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_usuario), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);
        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_ACCEPT);

        if (intentos > 0) {
            GtkWidget *lbl_error = gtk_label_new(NULL);
            gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
            gchar *texto_error = g_strdup_printf(
                "<span foreground='red'>Usuario o contrasena incorrectos. Intento %d de %d.</span>",
                intentos, max_intentos);
            gtk_label_set_markup(GTK_LABEL(lbl_error), texto_error);
            g_free(texto_error);
            gtk_box_pack_start(GTK_BOX(caja), lbl_error, FALSE, FALSE, 0);
        }

        gtk_widget_show_all(dialogo);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (respuesta != GTK_RESPONSE_ACCEPT) {
            gtk_widget_destroy(dialogo);
            return FALSE;
        }

        const char *usuario_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_usuario));
        const char *password_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_password));

        int rol_db = -1;
        /* El Administrador ya NO entra por aqui -- Colaborador es solo
         * para empleados (Veterinario, Voluntario). Si alguien intenta
         * usar las credenciales del Administrador en este login, se
         * trata igual que usuario/contrasena incorrectos. */
        gboolean ok = (usuario_autenticar(usuario_ingresado, password_ingresado, &rol_db) == 0
                       && rol_db != ROL_ADMIN);

        if (ok) {
            snprintf(usuario_out, usuario_len, "%s", usuario_ingresado);
            *rol_out = (Rol)rol_db;
            gtk_widget_destroy(dialogo);
            return TRUE;
        }

        gtk_widget_destroy(dialogo);
        intentos++;
    }

    GtkWidget *aviso = gtk_message_dialog_new(
        NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR, GTK_BUTTONS_OK,
        "Demasiados intentos fallidos. Cerrando PawOS.");
    gtk_dialog_run(GTK_DIALOG(aviso));
    gtk_widget_destroy(aviso);
    return FALSE;
}

/* Asistente de bienvenida: crea la cuenta del primer Administrador.
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
            /* Cerrar esta ventana (la X) o cancelar aqui cierra el
             * programa por completo -- antes esto volvia a abrir la
             * misma ventana en un ciclo infinito, sin forma de salir. */
            gtk_widget_destroy(dialogo);
            db_close();
            exit(0);
        }

        char usuario_copia[64];
        char pass1_copia[64];
        char pass2_copia[64];
        snprintf(usuario_copia, sizeof(usuario_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_user)));
        snprintf(pass1_copia, sizeof(pass1_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_pass)));
        snprintf(pass2_copia, sizeof(pass2_copia), "%s", gtk_entry_get_text(GTK_ENTRY(entrada_pass2)));
        gtk_widget_destroy(dialogo);

        const char *error = NULL;
        if (usuario_copia[0] == '\0') {
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

        if (usuario_registrar(usuario_copia, pass1_copia, ROL_ADMIN, "") == 0) {
            mostrar_mensaje(NULL, "Cuenta de Administrador creada. Ya puedes iniciar sesion.", FALSE);
            return;
        }
        mostrar_mensaje(NULL, "No se pudo crear la cuenta (ese usuario ya existe). Intenta con otro nombre.", TRUE);
    }
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    /* Modo claro/oscuro automatico: se aplica al iniciar segun la
     * preferencia del sistema, y se vuelve a aplicar solo si el usuario
     * cambia esa preferencia mientras PawOS esta abierto. Sin switch
     * propio en la app. */
    aplicar_estilos();
    GtkSettings *settings_sistema = gtk_settings_get_default();
    if (settings_sistema) {
        g_signal_connect(settings_sistema, "notify::gtk-application-prefer-dark-theme",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
        g_signal_connect(settings_sistema, "notify::gtk-theme-name",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
    }

    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;
    if (db_init(ruta_bd) != 0) {
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }

    if (!memoria_inicializar()) {
        fprintf(stderr, "Aviso: no se pudo inicializar el sistema de memoria.\n");
    }

    if (!existe_admin()) {
        mostrar_asistente_bienvenida();
    }

    for (;;) {
        TipoEntrada entrada = mostrar_selector_entrada();
        if (entrada == ENTRADA_CANCELAR) {
            break;
        }

        char nombre_sesion[64] = "";
        gboolean logueado = FALSE;

        if (entrada == ENTRADA_COLABORADOR) {
            char usuario[32] = "";
            Rol rol;
            if (mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
                snprintf(nombre_sesion, sizeof(nombre_sesion), "%s", usuario);
                construir_ventana_principal(rol, usuario);
                logueado = TRUE;
            }
        } else {
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
        }

        if (logueado) {
            gtk_main();
        }
        /* Si cancelo el login (boton "Regresar"), o si cerro la
         * ventana que se abrio, el ciclo vuelve a mostrar el selector
         * -- el programa NO se cierra solo por eso, unicamente con
         * "Salir" desde el selector inicial. */
    }

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto.\n");
    return 0;
}
