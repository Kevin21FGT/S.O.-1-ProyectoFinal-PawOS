/*
 * main_archivos_gui.c - PawOS Archivos
 *
 * App grafica standalone (GTK3), estilo explorador de archivos, para el
 * "sistema de archivos organizado" de PawOS: categorias a la izquierda
 * (mascotas, vacunas, adopciones, donantes, reportes, backups) y los
 * archivos de la categoria elegida a la derecha. Tambien incluye la
 * verificacion de integridad de donantes (checksum en Ensamblador) y el
 * respaldo de la base de datos.
 *
 * Reutiliza la logica ya existente, sin reimplementar nada de negocio:
 * archivos_inicializar/listar/eliminar/espacio_categoria/respaldar_bd_auto
 * (archivos.c) e integridad_verificar_donantes /
 * integridad_actualizar_checksum_donantes (integridad.c + checksum.asm).
 * Lo unico nuevo es "Agregar archivo" (copia con GIO) y "Abrir".
 */
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include "db/db.h"
#include "archivos/archivos.h"
#include "integridad/integridad.h"
#include "version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"

enum {
    COL_C_NOMBRE = 0,
    COL_C_ESPACIO,
    COL_C_CLAVE,
    N_COLUMNAS_CAT
};

enum {
    COL_A_NOMBRE = 0,
    COL_A_TAM,
    COL_A_FECHA,
    COL_A_BYTES,
    N_COLUMNAS_ARCH
};

typedef struct {
    GtkWidget        *ventana;
    GtkListStore     *store_cat;
    GtkListStore     *store_arch;
    GtkTreeSelection *sel_cat;
    GtkTreeSelection *sel_arch;
    GtkWidget        *lbl_titulo_cat;
    GtkWidget        *lbl_integridad;
    int               indice_cat;
} ContextoApp;

static void cargar_categorias(ContextoApp *ctx);
static void cargar_archivos(ContextoApp *ctx);

static void mostrar_mensaje(GtkWindow *padre, const char *texto, gboolean es_error) {
    GtkWidget *dialogo = gtk_message_dialog_new(padre, GTK_DIALOG_MODAL,
        es_error ? GTK_MESSAGE_ERROR : GTK_MESSAGE_INFO, GTK_BUTTONS_OK, "%s", texto);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

static gboolean confirmar(GtkWindow *padre, const char *texto) {
    GtkWidget *dialogo = gtk_message_dialog_new(padre, GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_YES_NO, "%s", texto);
    int resp = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
    return resp == GTK_RESPONSE_YES;
}

static void aplicar_estilos_simples(void) {
    GtkCssProvider *proveedor = gtk_css_provider_new();
    const char *css =
        "window { background-color: #F4F6F5; }"
        ".pawos-header {"
        "  background-image: linear-gradient(180deg, #23924B 0%, #12451F 100%);"
        "  padding: 16px 20px;"
        "}"
        ".pawos-header label { color: #FFFFFF; }"
        ".pawos-tarjeta {"
        "  background-color: #FFFFFF;"
        "  border-radius: 12px;"
        "  padding: 14px;"
        "  box-shadow: 0 2px 8px rgba(0,0,0,0.10);"
        "}"
        "button.pawos-accion {"
        "  background-image: none;"
        "  background-color: #23924B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-accion:hover { background-color: #1D7A3E; }"
        "button.pawos-peligro {"
        "  background-image: none;"
        "  background-color: #C0392B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-peligro:hover { background-color: #A5301F; }";
    gtk_css_provider_load_from_data(proveedor, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(), GTK_STYLE_PROVIDER(proveedor),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(proveedor);
}

/* ---------- Utilidades ---------- */

static gchar *formatear_tamano(long bytes) {
    if (bytes < 0) return g_strdup("-");
    return g_format_size((guint64)bytes);
}

static gchar *capitalizar(const char *texto) {
    gchar *copia = g_strdup(texto);
    if (copia[0] != '\0') copia[0] = (gchar)g_ascii_toupper(copia[0]);
    return copia;
}

/* Devuelve (g_free) la clave de la categoria elegida, o NULL si no hay. */
static gchar *categoria_seleccionada(ContextoApp *ctx) {
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(ctx->sel_cat, &modelo, &iter)) return NULL;
    gchar *clave = NULL;
    gtk_tree_model_get(modelo, &iter, COL_C_CLAVE, &clave, -1);
    return clave;
}

/* Devuelve (g_free) el nombre del archivo elegido, o NULL si no hay. */
static gchar *archivo_seleccionado(ContextoApp *ctx) {
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(ctx->sel_arch, &modelo, &iter)) return NULL;
    gchar *nombre = NULL;
    gtk_tree_model_get(modelo, &iter, COL_A_NOMBRE, &nombre, -1);
    return nombre;
}

/* ---------- Carga de datos ---------- */

static void cargar_categorias(ContextoApp *ctx) {
    int quedar = ctx->indice_cat;
    gtk_list_store_clear(ctx->store_cat);

    for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) {
        gchar *nombre = capitalizar(ARCHIVOS_CATEGORIAS[i]);
        gchar *espacio = formatear_tamano(archivos_espacio_categoria(ARCHIVOS_CATEGORIAS[i]));
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_cat, &iter);
        gtk_list_store_set(ctx->store_cat, &iter,
            COL_C_NOMBRE, nombre,
            COL_C_ESPACIO, espacio,
            COL_C_CLAVE, ARCHIVOS_CATEGORIAS[i],
            -1);
        g_free(nombre);
        g_free(espacio);
    }

    GtkTreePath *ruta = gtk_tree_path_new_from_indices(quedar, -1);
    gtk_tree_selection_select_path(ctx->sel_cat, ruta);
    gtk_tree_path_free(ruta);
}

static void cargar_archivos(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_arch);

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), "Selecciona una categoria");
        return;
    }

    ArchivoInfo *lista = NULL;
    int n = 0;
    if (archivos_listar(cat, &lista, &n) != 0) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), "No se pudo leer la carpeta");
        g_free(cat);
        return;
    }

    for (int i = 0; i < n; i++) {
        gchar *tam = formatear_tamano(lista[i].tamano_bytes);
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_arch, &iter);
        gtk_list_store_set(ctx->store_arch, &iter,
            COL_A_NOMBRE, lista[i].nombre,
            COL_A_TAM, tam,
            COL_A_FECHA, lista[i].fecha_mod,
            COL_A_BYTES, (gint64)lista[i].tamano_bytes,
            -1);
        g_free(tam);
    }
    free(lista);

    gchar *nombre_cat = capitalizar(cat);
    gchar *titulo = g_strdup_printf("%s  (%d archivo%s)", nombre_cat, n, n == 1 ? "" : "s");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), titulo);
    g_free(titulo);
    g_free(nombre_cat);
    g_free(cat);
}

/* ---------- Eventos de categorias y archivos ---------- */

static void on_categoria_cambiada(GtkTreeSelection *sel, gpointer datos) {
    ContextoApp *ctx = datos;
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
        GtkTreePath *ruta = gtk_tree_model_get_path(modelo, &iter);
        ctx->indice_cat = gtk_tree_path_get_indices(ruta)[0];
        gtk_tree_path_free(ruta);
    }
    cargar_archivos(ctx);
}

static void on_actualizar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    cargar_categorias(ctx);
}

static void on_agregar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero una categoria a la izquierda.", TRUE);
        return;
    }

    GtkWidget *selector = gtk_file_chooser_dialog_new("Agregar archivo", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_OPEN, "_Cancelar", GTK_RESPONSE_CANCEL, "_Agregar", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_select_multiple(GTK_FILE_CHOOSER(selector), TRUE);

    if (gtk_dialog_run(GTK_DIALOG(selector)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(selector);
        g_free(cat);
        return;
    }
    GSList *elegidos = gtk_file_chooser_get_filenames(GTK_FILE_CHOOSER(selector));
    gtk_widget_destroy(selector);

    int copiados = 0, omitidos = 0;
    for (GSList *l = elegidos; l != NULL; l = l->next) {
        const char *origen = l->data;
        gchar *nombre = g_path_get_basename(origen);
        if (strlen(nombre) >= ARCHIVOS_MAX_NOMBRE) {
            omitidos++;
            g_free(nombre);
            continue;
        }
        gchar *destino = g_build_filename(archivos_ruta_base(), cat, nombre, NULL);
        GFile *f_origen = g_file_new_for_path(origen);
        GFile *f_destino = g_file_new_for_path(destino);
        GError *error = NULL;
        if (g_file_copy(f_origen, f_destino, G_FILE_COPY_NONE, NULL, NULL, NULL, &error)) {
            copiados++;
        } else {
            omitidos++;
            g_clear_error(&error);
        }
        g_object_unref(f_origen);
        g_object_unref(f_destino);
        g_free(destino);
        g_free(nombre);
    }
    g_slist_free_full(elegidos, g_free);
    g_free(cat);

    cargar_categorias(ctx);

    gchar *msg;
    if (omitidos > 0) {
        msg = g_strdup_printf("Se agregaron %d archivo(s). %d no se pudieron agregar "
            "(ya existian con ese nombre, el nombre es muy largo o no hay permisos).", copiados, omitidos);
    } else {
        msg = g_strdup_printf("Se agregaron %d archivo(s).", copiados);
    }
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, omitidos > 0 && copiados == 0);
    g_free(msg);
}

static void abrir_seleccionado(ContextoApp *ctx) {
    gchar *cat = categoria_seleccionada(ctx);
    gchar *nombre = archivo_seleccionado(ctx);
    if (!cat || !nombre) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero un archivo de la lista.", TRUE);
        g_free(cat);
        g_free(nombre);
        return;
    }
    gchar *ruta = g_build_filename(archivos_ruta_base(), cat, nombre, NULL);
    gchar *uri = g_filename_to_uri(ruta, NULL, NULL);
    GError *error = NULL;
    if (!uri || !g_app_info_launch_default_for_uri(uri, NULL, &error)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "No se pudo abrir el archivo (no hay un programa asociado a ese tipo).", TRUE);
        g_clear_error(&error);
    }
    g_free(uri);
    g_free(ruta);
    g_free(cat);
    g_free(nombre);
}

static void on_abrir_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    abrir_seleccionado((ContextoApp *)datos);
}

static void on_archivo_activado(GtkTreeView *vista, GtkTreePath *ruta, GtkTreeViewColumn *col, gpointer datos) {
    (void)vista; (void)ruta; (void)col;
    abrir_seleccionado((ContextoApp *)datos);
}

static void on_eliminar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    gchar *cat = categoria_seleccionada(ctx);
    gchar *nombre = archivo_seleccionado(ctx);
    if (!cat || !nombre) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero un archivo de la lista.", TRUE);
        g_free(cat);
        g_free(nombre);
        return;
    }

    gchar *pregunta = g_strdup_printf("Eliminar \"%s\"?\nEsta accion no se puede deshacer.", nombre);
    gboolean si = confirmar(GTK_WINDOW(ctx->ventana), pregunta);
    g_free(pregunta);

    if (si) {
        if (archivos_eliminar(cat, nombre) == 0) {
            cargar_categorias(ctx);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo eliminar el archivo.", TRUE);
        }
    }
    g_free(cat);
    g_free(nombre);
}

/* ---------- Respaldo e integridad ---------- */

static void on_respaldar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    if (archivos_respaldar_bd_auto() == 0) {
        cargar_categorias(ctx);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Respaldo creado. Lo encuentras en la categoria Backups.", FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo crear el respaldo.", TRUE);
    }
}

static void poner_estado_integridad(ContextoApp *ctx, const char *texto, const char *color) {
    gchar *markup = g_markup_printf_escaped("<span foreground='%s' weight='bold'>%s</span>", color, texto);
    gtk_label_set_markup(GTK_LABEL(ctx->lbl_integridad), markup);
    g_free(markup);
}

static void on_verificar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    int r = integridad_verificar_donantes();
    switch (r) {
        case 0:
            poner_estado_integridad(ctx, "Integro: los registros de donantes no han cambiado.", "#1E8449");
            break;
        case 1:
            poner_estado_integridad(ctx,
                "ALERTA: los registros de donantes cambiaron desde la ultima verificacion.", "#C0392B");
            break;
        case 2:
            poner_estado_integridad(ctx,
                "Se creo la verificacion base ahora. Desde aqui se detectan los cambios.", "#2E86C1");
            break;
        default:
            poner_estado_integridad(ctx, "No se pudo verificar (revisa la conexion a la base de datos).", "#D68910");
            break;
    }
    cargar_categorias(ctx);
}

static void on_aceptar_cambios_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    if (!confirmar(GTK_WINDOW(ctx->ventana),
            "Esto toma el estado actual de los donantes como el correcto.\n"
            "Hazlo solo si los cambios fueron hechos por ti.\n\n¿Continuar?")) {
        return;
    }
    if (integridad_actualizar_checksum_donantes() == 0) {
        poner_estado_integridad(ctx, "Cambios aceptados: este estado es ahora la base de comparacion.", "#2E86C1");
        cargar_categorias(ctx);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar la nueva base de comparacion.", TRUE);
    }
}

/* ---------- Ventana principal ---------- */

static GtkTreeViewColumn *columna_texto(const char *titulo, int col_texto, int col_orden, gboolean expandir) {
    GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
        titulo, gtk_cell_renderer_text_new(), "text", col_texto, NULL);
    gtk_tree_view_column_set_resizable(col, TRUE);
    gtk_tree_view_column_set_expand(col, expandir);
    if (col_orden >= 0) gtk_tree_view_column_set_sort_column_id(col, col_orden);
    return col;
}

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Archivos");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 960, 620);
    gtk_window_set_position(GTK_WINDOW(ctx->ventana), GTK_WIN_POS_CENTER);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    /* Encabezado */
    GtkWidget *encabezado = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "pawos-header");
    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *ruta_esc = g_markup_escape_text(archivos_ruta_base(), -1);
    gchar *markup_titulo = g_strdup_printf(
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Archivos</span>  "
        "<span size='small'>v%s  -  %s</span>", PAWOS_VERSION, ruta_esc);
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    g_free(ruta_esc);
    gtk_box_pack_start(GTK_BOX(encabezado), lbl_titulo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), encabezado, FALSE, FALSE, 0);

    GtkWidget *contenido = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    gtk_container_set_border_width(GTK_CONTAINER(contenido), 16);
    gtk_box_pack_start(GTK_BOX(caja_raiz), contenido, TRUE, TRUE, 0);

    GtkWidget *principal = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 14);
    gtk_box_pack_start(GTK_BOX(contenido), principal, TRUE, TRUE, 0);

    /* Izquierda: categorias */
    GtkWidget *tarjeta_cat = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_cat), "pawos-tarjeta");
    gtk_widget_set_size_request(tarjeta_cat, 240, -1);
    GtkWidget *lbl_cat = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_cat), "<span weight='bold'>Categorias</span>");
    gtk_widget_set_halign(lbl_cat, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_cat), lbl_cat, FALSE, FALSE, 0);

    ctx->store_cat = gtk_list_store_new(N_COLUMNAS_CAT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *vista_cat = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_cat));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_cat), columna_texto("Carpeta", COL_C_NOMBRE, -1, TRUE));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_cat), columna_texto("Espacio", COL_C_ESPACIO, -1, FALSE));
    ctx->sel_cat = gtk_tree_view_get_selection(GTK_TREE_VIEW(vista_cat));
    gtk_tree_selection_set_mode(ctx->sel_cat, GTK_SELECTION_BROWSE);
    g_signal_connect(ctx->sel_cat, "changed", G_CALLBACK(on_categoria_cambiada), ctx);

    GtkWidget *scroll_cat = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_cat), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll_cat), vista_cat);
    gtk_box_pack_start(GTK_BOX(tarjeta_cat), scroll_cat, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(principal), tarjeta_cat, FALSE, FALSE, 0);

    /* Derecha: barra de acciones + tabla de archivos */
    GtkWidget *derecha = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_box_pack_start(GTK_BOX(principal), derecha, TRUE, TRUE, 0);

    GtkWidget *barra = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    ctx->lbl_titulo_cat = gtk_label_new("");
    gtk_widget_set_halign(ctx->lbl_titulo_cat, GTK_ALIGN_START);
    gtk_widget_set_hexpand(ctx->lbl_titulo_cat, TRUE);
    gtk_box_pack_start(GTK_BOX(barra), ctx->lbl_titulo_cat, TRUE, TRUE, 0);

    GtkWidget *btn_agregar = gtk_button_new_with_label("Agregar archivo");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_agregar), "pawos-accion");
    g_signal_connect(btn_agregar, "clicked", G_CALLBACK(on_agregar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_agregar, FALSE, FALSE, 0);

    GtkWidget *btn_abrir = gtk_button_new_with_label("Abrir");
    g_signal_connect(btn_abrir, "clicked", G_CALLBACK(on_abrir_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_abrir, FALSE, FALSE, 0);

    GtkWidget *btn_eliminar = gtk_button_new_with_label("Eliminar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_eliminar), "pawos-peligro");
    g_signal_connect(btn_eliminar, "clicked", G_CALLBACK(on_eliminar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_eliminar, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar");
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(derecha), barra, FALSE, FALSE, 0);

    GtkWidget *tarjeta_arch = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_arch), "pawos-tarjeta");
    gtk_widget_set_vexpand(tarjeta_arch, TRUE);

    ctx->store_arch = gtk_list_store_new(N_COLUMNAS_ARCH,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_INT64);
    GtkWidget *vista_arch = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_arch));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_texto("Nombre", COL_A_NOMBRE, COL_A_NOMBRE, TRUE));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_texto("Tamano", COL_A_TAM, COL_A_BYTES, FALSE));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_texto("Modificado", COL_A_FECHA, COL_A_FECHA, FALSE));
    ctx->sel_arch = gtk_tree_view_get_selection(GTK_TREE_VIEW(vista_arch));
    g_signal_connect(vista_arch, "row-activated", G_CALLBACK(on_archivo_activado), ctx);

    GtkWidget *scroll_arch = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_arch), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll_arch, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll_arch), vista_arch);
    gtk_box_pack_start(GTK_BOX(tarjeta_arch), scroll_arch, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(derecha), tarjeta_arch, TRUE, TRUE, 0);

    /* Abajo: integridad de donantes + respaldo */
    GtkWidget *fila_inferior = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 14);
    gtk_box_pack_start(GTK_BOX(contenido), fila_inferior, FALSE, FALSE, 0);

    GtkWidget *tarjeta_int = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_int), "pawos-tarjeta");
    gtk_widget_set_hexpand(tarjeta_int, TRUE);

    GtkWidget *lbl_int_titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_int_titulo), "<span weight='bold'>Integridad de donantes:</span>");
    gtk_box_pack_start(GTK_BOX(tarjeta_int), lbl_int_titulo, FALSE, FALSE, 0);

    ctx->lbl_integridad = gtk_label_new("Sin verificar todavia.");
    gtk_label_set_line_wrap(GTK_LABEL(ctx->lbl_integridad), TRUE);
    gtk_widget_set_halign(ctx->lbl_integridad, GTK_ALIGN_START);
    gtk_widget_set_hexpand(ctx->lbl_integridad, TRUE);
    gtk_box_pack_start(GTK_BOX(tarjeta_int), ctx->lbl_integridad, TRUE, TRUE, 0);

    GtkWidget *btn_verificar = gtk_button_new_with_label("Verificar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_verificar), "pawos-accion");
    g_signal_connect(btn_verificar, "clicked", G_CALLBACK(on_verificar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(tarjeta_int), btn_verificar, FALSE, FALSE, 0);

    GtkWidget *btn_aceptar = gtk_button_new_with_label("Aceptar cambios");
    g_signal_connect(btn_aceptar, "clicked", G_CALLBACK(on_aceptar_cambios_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(tarjeta_int), btn_aceptar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_inferior), tarjeta_int, TRUE, TRUE, 0);

    GtkWidget *btn_respaldar = gtk_button_new_with_label("Respaldar base de datos ahora");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_respaldar), "pawos-accion");
    g_signal_connect(btn_respaldar, "clicked", G_CALLBACK(on_respaldar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(fila_inferior), btn_respaldar, FALSE, FALSE, 0);

    gtk_widget_show_all(ctx->ventana);
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);

    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;
    if (db_init(ruta_bd) != 0) {
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }

    if (archivos_inicializar() != 0) {
        fprintf(stderr, "No se pudo preparar la carpeta de archivos de PawOS.\n");
        db_close();
        return 1;
    }

    aplicar_estilos_simples();

    ContextoApp ctx;
    memset(&ctx, 0, sizeof(ctx));

    construir_ventana(&ctx);
    cargar_categorias(&ctx);

    gtk_main();
    db_close();
    return 0;
}
