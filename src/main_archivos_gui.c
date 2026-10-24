/*
 * main_archivos_gui.c - PawOS Archivos
 *
 * App grafica standalone (GTK3), estilo explorador de archivos, para el
 * "sistema de archivos organizado" de PawOS: categorias a la izquierda
 * (mascotas, vacunas, adopciones, donantes, reportes, backups) y los
 * archivos/carpetas de la categoria elegida a la derecha. Dentro de cada
 * categoria se pueden crear subcarpetas y navegar por ellas. Tambien
 * incluye la verificacion de integridad de donantes (checksum en
 * Ensamblador) y el respaldo de los datos del SQL Server.
 *
 * Reutiliza la logica ya existente, sin reimplementar nada de negocio:
 * archivos_inicializar/listar/eliminar/respaldar_bd_auto (archivos.c),
 * integridad_verificar_donantes / integridad_actualizar_checksum_donantes
 * (integridad.c + checksum.asm) y las funciones *_listar de db.c.
 * Lo nuevo (hecho aqui con GLib/GIO): agregar archivo, abrir, crear y
 * navegar carpetas, y el respaldo CSV + tabla "respaldos".
 *
 * Nota: archivos_listar/archivos_eliminar arman la ruta como
 * "<base>/<categoria>/<nombre>", asi que una subcarpeta se maneja
 * pasando "<categoria>/<subcarpeta>" como categoria.
 */
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <glib/gstdio.h>
#include "db/db.h"
#include "archivos/archivos.h"
#include "integridad/integridad.h"
#include "version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define RUTA_MAX_SEGURA 230

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
    COL_A_ICONO,
    COL_A_ES_DIR,
    COL_A_NUBE,
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
    GtkWidget        *btn_atras;
    GtkWidget        *vista_cat;
    GtkWidget        *vista_arch;
    GtkWidget        *lbl_vacio;     /* "Esta carpeta esta vacia", sobre la lista */
    GtkTreeViewColumn *col_nube;     /* columna "En la nube" (solo en Backups) */
    gchar            *arrastre;      /* nombres arrastrados, separados por salto de linea (NULL = ninguno) */
    gboolean          bloquear_sel;  /* mientras se mantiene el clic sobre una seleccion multiple */
    gboolean          arrastrando;
    GtkTreePath      *clic_ruta;     /* fila sobre la que se hizo clic (seleccion multiple) */
    int               indice_cat;
    char              subruta[256]; /* carpeta abierta dentro de la categoria, "" = raiz */
} ContextoApp;

static void cargar_categorias(ContextoApp *ctx);
static void cargar_archivos(ContextoApp *ctx);
static void on_seleccionar_todo_clicked(GtkButton *btn, gpointer datos);
static void on_respaldar_carpeta_clicked(GtkButton *btn, gpointer datos);
static void on_respaldar_clicked(GtkButton *btn, gpointer datos);

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
        "button.pawos-peligro:hover { background-color: #A5301F; }"
        /* Barras de desplazamiento siempre visibles cuando hacen falta */
        "scrollbar { background-color: #E8ECEA; }"
        "scrollbar slider {"
        "  min-width: 10px; min-height: 10px;"
        "  background-color: #23924B;"
        "  border-radius: 6px;"
        "}"
        "scrollbar slider:hover { background-color: #1D7A3E; }";
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

/* Espacio total de una carpeta, contando lo que hay en sus subcarpetas. */
static long tamano_recursivo(const char *ruta) {
    GDir *d = g_dir_open(ruta, 0, NULL);
    if (!d) return 0;
    long total = 0;
    const char *nombre;
    while ((nombre = g_dir_read_name(d)) != NULL) {
        gchar *hijo = g_build_filename(ruta, nombre, NULL);
        GStatBuf st;
        if (g_stat(hijo, &st) == 0) {
            if (S_ISDIR(st.st_mode)) total += tamano_recursivo(hijo);
            else total += (long)st.st_size;
        }
        g_free(hijo);
    }
    g_dir_close(d);
    return total;
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

/* Devuelve los nombres de los elementos elegidos en la lista (puede estar
 * vacio, nunca NULL). Liberar con g_ptr_array_free(arr, TRUE). */
static GPtrArray *archivos_seleccionados(ContextoApp *ctx) {
    GPtrArray *res = g_ptr_array_new_with_free_func(g_free);
    GtkTreeModel *modelo = NULL;
    GList *filas = gtk_tree_selection_get_selected_rows(ctx->sel_arch, &modelo);
    for (GList *l = filas; l != NULL; l = l->next) {
        GtkTreeIter iter;
        if (gtk_tree_model_get_iter(modelo, &iter, l->data)) {
            gchar *nombre = NULL;
            gtk_tree_model_get(modelo, &iter, COL_A_NOMBRE, &nombre, -1);
            if (nombre) g_ptr_array_add(res, nombre);
        }
    }
    g_list_free_full(filas, (GDestroyNotify)gtk_tree_path_free);
    return res;
}

/* Ruta de la carpeta abierta, relativa a la base: "reportes" o
 * "reportes/2026". Es lo que se le pasa a archivos_listar/eliminar. */
static gchar *ruta_relativa_actual(ContextoApp *ctx, const char *cat) {
    if (ctx->subruta[0] == '\0') return g_strdup(cat);
    return g_build_filename(cat, ctx->subruta, NULL);
}

static void entrar_carpeta(ContextoApp *ctx, const char *nombre) {
    size_t usado = strlen(ctx->subruta);
    if (usado + strlen(nombre) + 2 >= sizeof(ctx->subruta)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "La ruta es demasiado larga.", TRUE);
        return;
    }
    if (usado > 0) snprintf(ctx->subruta + usado, sizeof(ctx->subruta) - usado, "/%s", nombre);
    else snprintf(ctx->subruta, sizeof(ctx->subruta), "%s", nombre);
    cargar_archivos(ctx);
}

/* ---------- Carga de datos ---------- */

static void cargar_categorias(ContextoApp *ctx) {
    int quedar = ctx->indice_cat;
    gtk_list_store_clear(ctx->store_cat);

    for (int i = 0; i < ARCHIVOS_NUM_CATEGORIAS; i++) {
        gchar *nombre = capitalizar(ARCHIVOS_CATEGORIAS[i]);
        gchar *dir_cat = g_build_filename(archivos_ruta_base(), ARCHIVOS_CATEGORIAS[i], NULL);
        gchar *espacio = formatear_tamano(tamano_recursivo(dir_cat));
        g_free(dir_cat);
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
    if (ctx->lbl_vacio) gtk_widget_set_visible(ctx->lbl_vacio, FALSE);

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), "Selecciona una categoria");
        gtk_widget_set_sensitive(ctx->btn_atras, FALSE);
        return;
    }
    gtk_widget_set_sensitive(ctx->btn_atras, ctx->subruta[0] != '\0');

    gchar *rel = ruta_relativa_actual(ctx, cat);
    /* Se lista aqui (y no con archivos_listar) porque esa funcion omite
     * las carpetas. */
    gchar *dir_actual = g_build_filename(archivos_ruta_base(), rel, NULL);
    GDir *gd = g_dir_open(dir_actual, 0, NULL);
    if (!gd) {
        gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), "No se pudo leer la carpeta");
        g_free(dir_actual);
        g_free(rel);
        g_free(cat);
        return;
    }
    GPtrArray *nombres = g_ptr_array_new_with_free_func(g_free);
    const char *entrada;
    while ((entrada = g_dir_read_name(gd)) != NULL) g_ptr_array_add(nombres, g_strdup(entrada));
    g_dir_close(gd);
    int n = (int)nombres->len;
    if (ctx->lbl_vacio) gtk_widget_set_visible(ctx->lbl_vacio, n == 0);

    /* En la raiz de Backups se marca que respaldos ya estan en SmarterASP
     * (una sola consulta). */
    gboolean modo_nube = (strcmp(cat, "backups") == 0 && ctx->subruta[0] == '\0');
    char **nubes = NULL;
    int n_nubes = 0;
    int rc_nube = modo_nube ? respaldo_listar_nombres(&nubes, &n_nubes) : 0;
    if (ctx->col_nube) gtk_tree_view_column_set_visible(ctx->col_nube, modo_nube);

    /* Primero las carpetas y despues los archivos */
    for (int pasada = 0; pasada < 2; pasada++) {
        for (guint i = 0; i < nombres->len; i++) {
            const char *nom = g_ptr_array_index(nombres, i);
            gchar *completa = g_build_filename(dir_actual, nom, NULL);
            GStatBuf st;
            if (g_stat(completa, &st) != 0) { g_free(completa); continue; }
            g_free(completa);
            gboolean es_dir = S_ISDIR(st.st_mode);
            if (es_dir != (pasada == 0)) continue;

            gchar *tam = es_dir ? g_strdup("-") : formatear_tamano((long)st.st_size);
            char fecha[24];
            struct tm tmv;
            time_t mt = st.st_mtime;
            localtime_r(&mt, &tmv);
            strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M", &tmv);
            const char *nube_txt = "";
            if (modo_nube && es_dir) {
                if (rc_nube != 0) {
                    nube_txt = "?";
                } else {
                    nube_txt = "No";
                    for (int k = 0; k < n_nubes; k++) {
                        if (strcmp(nubes[k], nom) == 0) { nube_txt = "Si"; break; }
                    }
                }
            }
            GtkTreeIter iter;
            gtk_list_store_append(ctx->store_arch, &iter);
            gtk_list_store_set(ctx->store_arch, &iter,
                COL_A_NOMBRE, nom,
                COL_A_TAM, tam,
                COL_A_FECHA, fecha,
                COL_A_BYTES, es_dir ? (gint64)-1 : (gint64)st.st_size,
                COL_A_ICONO, es_dir ? "folder" : "text-x-generic",
                COL_A_ES_DIR, es_dir,
                COL_A_NUBE, nube_txt,
                -1);
            g_free(tam);
        }
    }
    g_ptr_array_free(nombres, TRUE);
    g_free(dir_actual);
    for (int k = 0; k < n_nubes; k++) free(nubes[k]);
    free(nubes);

    gchar *nombre_cat = capitalizar(cat);
    gchar *ruta_txt;
    if (ctx->subruta[0] != '\0') {
        gchar **partes = g_strsplit(ctx->subruta, "/", -1);
        gchar *unido = g_strjoinv(" > ", partes);
        ruta_txt = g_strdup_printf("%s > %s", nombre_cat, unido);
        g_free(unido);
        g_strfreev(partes);
    } else {
        ruta_txt = g_strdup(nombre_cat);
    }
    gchar *titulo = g_strdup_printf("%s  (%d elemento%s)", ruta_txt, n, n == 1 ? "" : "s");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_titulo_cat), titulo);
    g_free(titulo);
    g_free(ruta_txt);
    g_free(nombre_cat);
    g_free(rel);
    g_free(cat);
}

/* ---------- Eventos de categorias y archivos ---------- */

static void on_categoria_cambiada(GtkTreeSelection *sel, gpointer datos) {
    ContextoApp *ctx = datos;
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (gtk_tree_selection_get_selected(sel, &modelo, &iter)) {
        GtkTreePath *ruta = gtk_tree_model_get_path(modelo, &iter);
        int nuevo = gtk_tree_path_get_indices(ruta)[0];
        /* Al cambiar de categoria se vuelve a la raiz. Si solo se
         * refresca la misma, se queda en la carpeta que estaba abierta. */
        if (nuevo != ctx->indice_cat) ctx->subruta[0] = '\0';
        ctx->indice_cat = nuevo;
        gtk_tree_path_free(ruta);
    }
    cargar_archivos(ctx);
}

static void on_actualizar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    cargar_categorias(ctx);
}

static void on_atras_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    char *ultimo = strrchr(ctx->subruta, '/');
    if (ultimo) *ultimo = '\0';
    else ctx->subruta[0] = '\0';
    cargar_archivos(ctx);
}

static void on_nueva_carpeta_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero una categoria a la izquierda.", TRUE);
        return;
    }
    gchar *rel = ruta_relativa_actual(ctx, cat);

    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Nueva carpeta", GTK_WINDOW(ctx->ventana),
        GTK_DIALOG_MODAL, "_Cancelar", GTK_RESPONSE_CANCEL, "_Crear", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 360, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);

    GtkWidget *lbl = gtk_label_new("Nombre de la carpeta:");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);

    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);

    GtkWidget *lbl_error = gtk_label_new("");
    gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
    gtk_widget_set_no_show_all(lbl_error, TRUE);
    gtk_box_pack_start(GTK_BOX(area), lbl_error, FALSE, FALSE, 0);

    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    gboolean creada = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        gchar *nombre = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        const char *error = NULL;

        if (nombre[0] == '\0') error = "Escribe un nombre para la carpeta.";
        else if (strchr(nombre, '/') || strchr(nombre, '\\')) error = "El nombre no puede contener / ni \\.";
        else if (strcmp(nombre, ".") == 0 || strcmp(nombre, "..") == 0) error = "Ese nombre no es valido.";
        else if (strlen(nombre) >= ARCHIVOS_MAX_NOMBRE) error = "El nombre es demasiado largo.";
        else if (strlen(archivos_ruta_base()) + strlen(rel) + strlen(nombre) >= RUTA_MAX_SEGURA)
            error = "La ruta quedaria demasiado larga.";

        gchar *completa = NULL;
        if (!error) {
            completa = g_build_filename(archivos_ruta_base(), rel, nombre, NULL);
            if (g_file_test(completa, G_FILE_TEST_EXISTS)) error = "Ya existe un archivo o carpeta con ese nombre.";
            else if (g_mkdir(completa, 0770) != 0) error = "No se pudo crear la carpeta (revisa los permisos).";
        }

        if (error) {
            gchar *markup = g_markup_printf_escaped("<span size='small' foreground='#C0392B'>%s</span>", error);
            gtk_label_set_markup(GTK_LABEL(lbl_error), markup);
            g_free(markup);
            gtk_widget_set_no_show_all(lbl_error, FALSE);
            gtk_widget_show(lbl_error);
            g_free(completa);
            g_free(nombre);
            continue;
        }

        g_free(completa);
        g_free(nombre);
        creada = TRUE;
        break;
    }
    gtk_widget_destroy(dialogo);
    g_free(rel);
    g_free(cat);

    if (creada) cargar_categorias(ctx);
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

    gchar *rel = ruta_relativa_actual(ctx, cat);
    int copiados = 0, omitidos = 0;
    for (GSList *l = elegidos; l != NULL; l = l->next) {
        const char *origen = l->data;
        gchar *nombre = g_path_get_basename(origen);
        if (strlen(nombre) >= ARCHIVOS_MAX_NOMBRE) {
            omitidos++;
            g_free(nombre);
            continue;
        }
        gchar *destino = g_build_filename(archivos_ruta_base(), rel, nombre, NULL);
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
    g_free(rel);
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

/* Si lo elegido es una carpeta, entra en ella; si es un archivo, lo
 * abre con el programa predeterminado del sistema. */
static void abrir_seleccionado(ContextoApp *ctx) {
    gchar *cat = categoria_seleccionada(ctx);
    GPtrArray *sel = archivos_seleccionados(ctx);
    if (!cat || sel->len == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero un archivo o carpeta de la lista.", TRUE);
        g_free(cat);
        g_ptr_array_free(sel, TRUE);
        return;
    }
    if (sel->len > 1) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige un solo elemento para abrirlo.", FALSE);
        g_free(cat);
        g_ptr_array_free(sel, TRUE);
        return;
    }
    gchar *nombre = g_strdup(g_ptr_array_index(sel, 0));
    g_ptr_array_free(sel, TRUE);
    gchar *rel = ruta_relativa_actual(ctx, cat);
    gchar *ruta = g_build_filename(archivos_ruta_base(), rel, nombre, NULL);
    g_free(rel);

    if (g_file_test(ruta, G_FILE_TEST_IS_DIR)) {
        entrar_carpeta(ctx, nombre);
        g_free(ruta);
        g_free(cat);
        g_free(nombre);
        return;
    }

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
    GPtrArray *sel = archivos_seleccionados(ctx);
    if (!cat || sel->len == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero un archivo o carpeta de la lista.", TRUE);
        g_free(cat);
        g_ptr_array_free(sel, TRUE);
        return;
    }

    gchar *pregunta;
    if (sel->len == 1)
        pregunta = g_strdup_printf("Eliminar \"%s\"?\nEsta accion no se puede deshacer.",
            (const char *)g_ptr_array_index(sel, 0));
    else
        pregunta = g_strdup_printf("Eliminar los %u elementos seleccionados?\nEsta accion no se puede deshacer.",
            sel->len);
    gboolean si = confirmar(GTK_WINDOW(ctx->ventana), pregunta);
    g_free(pregunta);

    if (si) {
        gchar *rel = ruta_relativa_actual(ctx, cat);
        int fallidos = 0, carpetas = 0;
        for (guint i = 0; i < sel->len; i++) {
            const char *nombre = g_ptr_array_index(sel, i);
            gchar *completa = g_build_filename(archivos_ruta_base(), rel, nombre, NULL);
            if (g_file_test(completa, G_FILE_TEST_IS_DIR)) {
                if (g_rmdir(completa) != 0) { fallidos++; carpetas++; }
            } else if (archivos_eliminar(rel, nombre) != 0) {
                fallidos++;
            }
            g_free(completa);
        }
        g_free(rel);
        cargar_categorias(ctx);
        if (fallidos > 0) {
            gchar *msg = g_strdup_printf("%d elemento(s) no se pudieron eliminar.%s", fallidos,
                carpetas > 0 ? "\nLas carpetas solo se eliminan si estan vacias." : "");
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
            g_free(msg);
        }
    }
    g_free(cat);
    g_ptr_array_free(sel, TRUE);
}

/* Renombra el elemento marcado (clic derecho > Renombrar, o F2). */
static void on_renombrar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    gchar *cat = categoria_seleccionada(ctx);
    GPtrArray *sel = archivos_seleccionados(ctx);
    if (!cat || sel->len != 1) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Marca un solo elemento para renombrarlo.", TRUE);
        g_free(cat);
        g_ptr_array_free(sel, TRUE);
        return;
    }
    gchar *viejo = g_strdup(g_ptr_array_index(sel, 0));
    g_ptr_array_free(sel, TRUE);
    gchar *rel = ruta_relativa_actual(ctx, cat);
    g_free(cat);
    gchar *ruta_vieja = g_build_filename(archivos_ruta_base(), rel, viejo, NULL);
    gboolean es_dir = g_file_test(ruta_vieja, G_FILE_TEST_IS_DIR);

    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Renombrar", GTK_WINDOW(ctx->ventana),
        GTK_DIALOG_MODAL, "_Cancelar", GTK_RESPONSE_CANCEL, "_Renombrar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 380, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);
    GtkWidget *lbl = gtk_label_new("Nuevo nombre:");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entrada), viejo);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);
    GtkWidget *lbl_error = gtk_label_new("");
    gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
    gtk_widget_set_no_show_all(lbl_error, TRUE);
    gtk_box_pack_start(GTK_BOX(area), lbl_error, FALSE, FALSE, 0);
    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    /* En archivos se selecciona solo el nombre, sin la extension */
    const char *punto = es_dir ? NULL : strrchr(viejo, '.');
    int fin = (punto && punto != viejo) ? (int)g_utf8_strlen(viejo, punto - viejo) : -1;
    gtk_editable_select_region(GTK_EDITABLE(entrada), 0, fin);

    gboolean cambio = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;
        gchar *nuevo = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        const char *error = NULL;
        if (strcmp(nuevo, viejo) == 0) { g_free(nuevo); break; }
        if (nuevo[0] == '\0') error = "Escribe un nombre.";
        else if (strchr(nuevo, '/') || strchr(nuevo, '\\')) error = "El nombre no puede contener / ni \\.";
        else if (strcmp(nuevo, ".") == 0 || strcmp(nuevo, "..") == 0) error = "Ese nombre no es valido.";
        else if (strlen(nuevo) >= ARCHIVOS_MAX_NOMBRE) error = "El nombre es demasiado largo.";
        gchar *ruta_nueva = NULL;
        if (!error) {
            ruta_nueva = g_build_filename(archivos_ruta_base(), rel, nuevo, NULL);
            if (g_file_test(ruta_nueva, G_FILE_TEST_EXISTS)) error = "Ya existe algo con ese nombre.";
            else if (g_rename(ruta_vieja, ruta_nueva) != 0) error = "No se pudo renombrar (revisa los permisos).";
        }
        g_free(ruta_nueva);
        if (error) {
            gchar *markup = g_markup_printf_escaped("<span size='small' foreground='#C0392B'>%s</span>", error);
            gtk_label_set_markup(GTK_LABEL(lbl_error), markup);
            g_free(markup);
            gtk_widget_set_no_show_all(lbl_error, FALSE);
            gtk_widget_show(lbl_error);
            g_free(nuevo);
            continue;
        }
        g_free(nuevo);
        cambio = TRUE;
        break;
    }
    gtk_widget_destroy(dialogo);
    g_free(ruta_vieja);
    g_free(viejo);
    g_free(rel);
    if (cambio) cargar_categorias(ctx);
}

/* ---------- Menu de clic derecho y atajos de teclado ---------- */

/* Guarda las fotos de las mascotas (JPEG en base64 en la BD) como archivos
 * <id>_<nombre>.jpg dentro de `dir`. La carpeta se crea con la primera foto.
 * Devuelve cuantas se guardaron, o -1 si no se pudo leer la lista. */
static int exportar_fotos_mascotas(const char *dir) {
    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar(&ms, &n) != 0) return -1;
    int guardadas = 0;
    gboolean dir_lista = FALSE;
    for (int i = 0; i < n; i++) {
        char *b64 = NULL;
        if (mascota_obtener_foto(ms[i].id, &b64) != 0 || !b64 || !b64[0]) { free(b64); continue; }
        gsize largo = 0;
        guchar *bytes = g_base64_decode(b64, &largo);
        free(b64);
        if (bytes && largo > 0) {
            if (!dir_lista) dir_lista = (g_mkdir_with_parents(dir, 0770) == 0);
            if (dir_lista) {
                gchar *seguro = g_strdup(ms[i].nombre);
                for (gchar *p = seguro; *p; p++)
                    if ((guchar)*p < 128 && !g_ascii_isalnum(*p)) *p = '_';
                gchar *nombre = g_strdup_printf("%d_%s.jpg", ms[i].id, seguro);
                gchar *ruta = g_build_filename(dir, nombre, NULL);
                if (g_file_set_contents(ruta, (const gchar *)bytes, (gssize)largo, NULL)) guardadas++;
                g_free(ruta);
                g_free(nombre);
                g_free(seguro);
            }
        }
        g_free(bytes);
    }
    free(ms);
    return guardadas;
}

/* Desde el menu se difiere (el menu se destruye al elegir una opcion). */
static gboolean exportar_fotos_diferido(gpointer datos) {
    ContextoApp *ctx = datos;
    gchar *cat = categoria_seleccionada(ctx);
    if (!cat || strcmp(cat, "mascotas") != 0) { g_free(cat); return G_SOURCE_REMOVE; }
    gchar *rel = ruta_relativa_actual(ctx, cat);
    gchar *dir = g_build_filename(archivos_ruta_base(), rel, "fotos_mascotas", NULL);
    int n = exportar_fotos_mascotas(dir);
    if (n < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "No se pudieron leer las mascotas (revisa la conexion) o crear la carpeta.", TRUE);
    } else if (n == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Ninguna mascota tiene foto todavia.", FALSE);
    } else {
        cargar_archivos(ctx);
        gchar *msg = g_strdup_printf("%d foto%s exportada%s a la carpeta \"fotos_mascotas\".",
                                     n, n == 1 ? "" : "s", n == 1 ? "" : "s");
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
        g_free(msg);
    }
    g_free(dir);
    g_free(rel);
    g_free(cat);
    return G_SOURCE_REMOVE;
}

static void on_exportar_fotos_desde_menu(GtkMenuItem *item, gpointer datos) {
    (void)item;
    g_idle_add(exportar_fotos_diferido, datos);
}

static void agregar_item_menu(GtkWidget *menu, const char *texto, GCallback cb, ContextoApp *ctx, gboolean activo) {
    GtkWidget *item = gtk_menu_item_new_with_label(texto);
    gtk_widget_set_sensitive(item, activo);
    g_signal_connect(item, "activate", cb, ctx);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), item);
}

/* Desde el menu se difiere la accion: el menu se destruye al elegir una
 * opcion y el respaldo abre cuadros de dialogo. */
static gboolean respaldar_diferido(gpointer datos) {
    on_respaldar_clicked(NULL, datos);
    return G_SOURCE_REMOVE;
}

static void on_respaldar_desde_menu(GtkMenuItem *item, gpointer datos) {
    (void)item;
    g_idle_add(respaldar_diferido, datos);
}

static void mostrar_menu_contextual(ContextoApp *ctx, GdkEventButton *ev) {
    gint n = gtk_tree_selection_count_selected_rows(ctx->sel_arch);

    /* Respaldar carpeta solo si hay exactamente una carpeta marcada */
    gboolean una_carpeta = FALSE;
    if (n == 1) {
        GtkTreeModel *modelo = NULL;
        GList *filas = gtk_tree_selection_get_selected_rows(ctx->sel_arch, &modelo);
        GtkTreeIter iter;
        if (filas && gtk_tree_model_get_iter(modelo, &iter, filas->data))
            gtk_tree_model_get(modelo, &iter, COL_A_ES_DIR, &una_carpeta, -1);
        g_list_free_full(filas, (GDestroyNotify)gtk_tree_path_free);
    }

    GtkWidget *menu = gtk_menu_new();
    agregar_item_menu(menu, "Abrir", G_CALLBACK(on_abrir_clicked), ctx, n == 1);
    agregar_item_menu(menu, "Renombrar  (F2)", G_CALLBACK(on_renombrar_clicked), ctx, n == 1);
    agregar_item_menu(menu, "Eliminar  (Supr)", G_CALLBACK(on_eliminar_clicked), ctx, n >= 1);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), gtk_separator_menu_item_new());
    agregar_item_menu(menu, "Nueva carpeta", G_CALLBACK(on_nueva_carpeta_clicked), ctx, TRUE);
    agregar_item_menu(menu, "Seleccionar todo  (Ctrl+A)", G_CALLBACK(on_seleccionar_todo_clicked), ctx, TRUE);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), gtk_separator_menu_item_new());
    agregar_item_menu(menu, "Respaldar carpeta", G_CALLBACK(on_respaldar_carpeta_clicked), ctx, una_carpeta);
    agregar_item_menu(menu, "Respaldar datos ahora", G_CALLBACK(on_respaldar_desde_menu), ctx, n == 0);
    {
        gchar *cat_menu = categoria_seleccionada(ctx);
        if (cat_menu && strcmp(cat_menu, "mascotas") == 0)
            agregar_item_menu(menu, "Exportar fotos de mascotas aqui",
                              G_CALLBACK(on_exportar_fotos_desde_menu), ctx, TRUE);
        g_free(cat_menu);
    }
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), gtk_separator_menu_item_new());
    agregar_item_menu(menu, "Actualizar", G_CALLBACK(on_actualizar_clicked), ctx, TRUE);
    gtk_widget_show_all(menu);
    g_signal_connect(menu, "selection-done", G_CALLBACK(gtk_widget_destroy), NULL);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent *)ev);
}

static gboolean on_lista_tecla(GtkWidget *w, GdkEventKey *ev, gpointer datos) {
    (void)w;
    if (ev->keyval == GDK_KEY_F2) {
        on_renombrar_clicked(NULL, datos);
        return TRUE;
    }
    if (ev->keyval == GDK_KEY_Delete || ev->keyval == GDK_KEY_KP_Delete) {
        on_eliminar_clicked(NULL, datos);
        return TRUE;
    }
    return FALSE;
}

/* Clic en un espacio vacio de la lista: se deselecciona todo (como en
 * Windows). Devuelve FALSE para que el recuadro de seleccion siga
 * funcionando. */
static gboolean on_lista_clic(GtkWidget *w, GdkEventButton *ev, gpointer datos) {
    ContextoApp *ctx = datos;
    GtkTreeView *vista = GTK_TREE_VIEW(w);

    /* Clic derecho: se marca el elemento bajo el cursor (si no estaba
     * marcado) y se abre el menu contextual. */
    if (ev->button == 3 && ev->window == gtk_tree_view_get_bin_window(vista)) {
        GtkTreePath *fila = NULL;
        if (gtk_tree_view_get_path_at_pos(vista, (gint)ev->x, (gint)ev->y, &fila, NULL, NULL, NULL)) {
            if (!gtk_tree_selection_path_is_selected(ctx->sel_arch, fila)) {
                gtk_tree_selection_unselect_all(ctx->sel_arch);
                gtk_tree_selection_select_path(ctx->sel_arch, fila);
            }
            gtk_tree_path_free(fila);
        } else {
            gtk_tree_selection_unselect_all(ctx->sel_arch);
        }
        mostrar_menu_contextual(ctx, ev);
        return TRUE;
    }

    if (ev->button != 1 || ev->window != gtk_tree_view_get_bin_window(vista)) return FALSE;
    if (ev->state & (GDK_CONTROL_MASK | GDK_SHIFT_MASK)) return FALSE;
    GtkTreePath *ruta = NULL;
    if (gtk_tree_view_get_path_at_pos(vista, (gint)ev->x, (gint)ev->y, &ruta, NULL, NULL, NULL)) {
        /* Clic sobre un elemento que ya forma parte de una seleccion
         * multiple: se bloquea el cambio de seleccion para poder
         * arrastrarlos todos. Si no hay arrastre, al soltar el boton
         * se queda seleccionado solo ese elemento. */
        if (ev->type == GDK_BUTTON_PRESS
            && gtk_tree_selection_path_is_selected(ctx->sel_arch, ruta)
            && gtk_tree_selection_count_selected_rows(ctx->sel_arch) > 1) {
            if (ctx->clic_ruta) gtk_tree_path_free(ctx->clic_ruta);
            ctx->clic_ruta = ruta;
            ctx->bloquear_sel = TRUE;
            ctx->arrastrando = FALSE;
        } else {
            gtk_tree_path_free(ruta);
        }
    } else {
        gtk_tree_selection_unselect_all(ctx->sel_arch);
    }
    return FALSE;
}

static gboolean on_lista_soltar(GtkWidget *w, GdkEventButton *ev, gpointer datos) {
    (void)w; (void)ev;
    ContextoApp *ctx = datos;
    if (!ctx->bloquear_sel) return FALSE;
    ctx->bloquear_sel = FALSE;
    if (ctx->clic_ruta && !ctx->arrastrando) {
        gtk_tree_selection_unselect_all(ctx->sel_arch);
        gtk_tree_selection_select_path(ctx->sel_arch, ctx->clic_ruta);
    }
    if (ctx->clic_ruta) {
        gtk_tree_path_free(ctx->clic_ruta);
        ctx->clic_ruta = NULL;
    }
    return FALSE;
}

/* Permite o veta los cambios de seleccion (ver on_lista_clic). */
static gboolean permitir_cambio_seleccion(GtkTreeSelection *sel, GtkTreeModel *modelo,
                                          GtkTreePath *ruta, gboolean seleccionado, gpointer datos) {
    (void)sel; (void)modelo; (void)ruta; (void)seleccionado;
    ContextoApp *ctx = datos;
    return !ctx->bloquear_sel;
}

static void on_seleccionar_todo_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    gtk_tree_selection_select_all(ctx->sel_arch);
}

/* ---------- Mover arrastrando ----------
 * Se arrastra un archivo/carpeta de la lista y se suelta sobre: una
 * carpeta de la lista, una categoria (a su raiz) o el boton "Atras"
 * (a la carpeta superior). Se usa la accion COPY solo para que GTK no
 * borre la fila por su cuenta; el movimiento real lo hace mover_a(). */

static const GtkTargetEntry TARGETS_MOVER[] = {
    { (gchar *)"PAWOS_ITEM", GTK_TARGET_SAME_APP, 0 }
};

/* Mueve un elemento. Devuelve NULL si salio bien o el texto del error. */
static const char *mover_uno(const char *rel_org, const char *rel_dest, const char *nombre) {
    gchar *origen = g_build_filename(archivos_ruta_base(), rel_org, nombre, NULL);
    gchar *destino = g_build_filename(archivos_ruta_base(), rel_dest, nombre, NULL);
    gboolean origen_es_dir = g_file_test(origen, G_FILE_TEST_IS_DIR);
    const char *error = NULL;

    if (g_file_test(destino, G_FILE_TEST_EXISTS)) {
        error = "Ya existe un archivo o carpeta con ese nombre en el destino.";
    } else if (origen_es_dir) {
        gchar *prefijo = g_strconcat(origen, "/", NULL);
        gchar *dir_dest = g_build_filename(archivos_ruta_base(), rel_dest, NULL);
        if (strcmp(dir_dest, origen) == 0 || g_str_has_prefix(dir_dest, prefijo))
            error = "No se puede mover una carpeta dentro de si misma.";
        g_free(prefijo);
        g_free(dir_dest);
    }

    if (!error && g_rename(origen, destino) != 0) {
        /* Si rename falla (otro disco), los archivos se copian y se borra el original. */
        gboolean ok = FALSE;
        if (!origen_es_dir) {
            GFile *fo = g_file_new_for_path(origen);
            GFile *fd = g_file_new_for_path(destino);
            if (g_file_copy(fo, fd, G_FILE_COPY_NONE, NULL, NULL, NULL, NULL)) {
                g_unlink(origen);
                ok = TRUE;
            }
            g_object_unref(fo);
            g_object_unref(fd);
        }
        if (!ok) error = "No se pudo mover (revisa los permisos).";
    }

    g_free(origen);
    g_free(destino);
    return error;
}

static void mover_a(ContextoApp *ctx, const char *rel_dest) {
    gchar *cat = categoria_seleccionada(ctx);
    if (!cat || !ctx->arrastre) { g_free(cat); return; }
    gchar *rel_org = ruta_relativa_actual(ctx, cat);
    g_free(cat);
    if (strcmp(rel_org, rel_dest) == 0) {
        g_free(rel_org);
        g_clear_pointer(&ctx->arrastre, g_free);
        return;
    }

    const char *error = NULL;
    gchar **nombres = g_strsplit(ctx->arrastre, "\n", -1);
    for (int i = 0; nombres[i] != NULL; i++) {
        if (nombres[i][0] == '\0') continue;
        const char *e = mover_uno(rel_org, rel_dest, nombres[i]);
        if (e && !error) error = e;
    }
    g_strfreev(nombres);
    g_free(rel_org);
    g_clear_pointer(&ctx->arrastre, g_free);

    if (error) mostrar_mensaje(GTK_WINDOW(ctx->ventana), error, TRUE);
    cargar_categorias(ctx);
}

static gboolean arrastre_contiene(ContextoApp *ctx, const char *nombre) {
    if (!ctx->arrastre) return FALSE;
    gboolean esta = FALSE;
    gchar **nombres = g_strsplit(ctx->arrastre, "\n", -1);
    for (int i = 0; nombres[i] != NULL; i++) {
        if (strcmp(nombres[i], nombre) == 0) { esta = TRUE; break; }
    }
    g_strfreev(nombres);
    return esta;
}

/* Devuelve (g_free) la carpeta destino relativa a la base para el punto
 * (x, y) sobre el widget "w", o NULL si ahi no se puede soltar. */
static gchar *destino_para(ContextoApp *ctx, GtkWidget *w, gint x, gint y, GtkTreePath **fila_out) {
    if (fila_out) *fila_out = NULL;
    if (!ctx->arrastre) return NULL;

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) return NULL;
    gchar *resultado = NULL;

    if (w == ctx->btn_atras) {
        if (ctx->subruta[0] != '\0') {
            gchar *padre = g_strdup(ctx->subruta);
            char *ult = strrchr(padre, '/');
            if (ult) *ult = '\0'; else padre[0] = '\0';
            resultado = (padre[0] != '\0') ? g_build_filename(cat, padre, NULL) : g_strdup(cat);
            g_free(padre);
        }
    } else if (GTK_IS_TREE_VIEW(w)) {
        GtkTreeView *vista = GTK_TREE_VIEW(w);
        GtkTreePath *ruta = NULL;
        if (gtk_tree_view_get_dest_row_at_pos(vista, x, y, &ruta, NULL) && ruta) {
            GtkTreeModel *modelo = gtk_tree_view_get_model(vista);
            GtkTreeIter iter;
            if (gtk_tree_model_get_iter(modelo, &iter, ruta)) {
                if (w == ctx->vista_cat) {
                    gchar *clave = NULL;
                    gtk_tree_model_get(modelo, &iter, COL_C_CLAVE, &clave, -1);
                    if (clave) { resultado = g_strdup(clave); g_free(clave); }
                } else {
                    gchar *nombre = NULL;
                    gboolean es_dir = FALSE;
                    gtk_tree_model_get(modelo, &iter, COL_A_NOMBRE, &nombre, COL_A_ES_DIR, &es_dir, -1);
                    if (nombre && es_dir && !arrastre_contiene(ctx, nombre)) {
                        gchar *rel = ruta_relativa_actual(ctx, cat);
                        resultado = g_build_filename(rel, nombre, NULL);
                        g_free(rel);
                    }
                    g_free(nombre);
                }
            }
            if (resultado && fila_out) *fila_out = gtk_tree_path_copy(ruta);
            gtk_tree_path_free(ruta);
        }
    }
    g_free(cat);
    return resultado;
}

static void quitar_resaltado(GtkWidget *w) {
    if (GTK_IS_TREE_VIEW(w))
        gtk_tree_view_set_drag_dest_row(GTK_TREE_VIEW(w), NULL, GTK_TREE_VIEW_DROP_INTO_OR_AFTER);
}

static void on_arrastre_inicio(GtkWidget *w, GdkDragContext *c, gpointer datos) {
    (void)w; (void)c;
    ContextoApp *ctx = datos;
    /* Ya empezo el arrastre: se mantiene la seleccion tal cual esta. */
    ctx->arrastrando = TRUE;
    ctx->bloquear_sel = FALSE;
    if (ctx->clic_ruta) {
        gtk_tree_path_free(ctx->clic_ruta);
        ctx->clic_ruta = NULL;
    }
    g_clear_pointer(&ctx->arrastre, g_free);
    GPtrArray *sel = archivos_seleccionados(ctx);
    if (sel->len > 0) {
        g_ptr_array_add(sel, NULL);
        ctx->arrastre = g_strjoinv("\n", (gchar **)sel->pdata);
    }
    g_ptr_array_free(sel, TRUE);
}

static void on_arrastre_datos(GtkWidget *w, GdkDragContext *c, GtkSelectionData *sd,
                              guint info, guint t, gpointer datos) {
    (void)w; (void)c; (void)info; (void)t;
    ContextoApp *ctx = datos;
    const char *txt = ctx->arrastre ? ctx->arrastre : "";
    gtk_selection_data_set(sd, gdk_atom_intern_static_string("PAWOS_ITEM"), 8,
        (const guchar *)txt, (gint)strlen(txt));
}

static gboolean on_dnd_motion(GtkWidget *w, GdkDragContext *c, gint x, gint y, guint t, gpointer datos) {
    ContextoApp *ctx = datos;
    GtkTreePath *fila = NULL;
    gchar *dest = destino_para(ctx, w, x, y, &fila);
    if (GTK_IS_TREE_VIEW(w)) {
        if (dest && fila)
            gtk_tree_view_set_drag_dest_row(GTK_TREE_VIEW(w), fila, GTK_TREE_VIEW_DROP_INTO_OR_AFTER);
        else
            quitar_resaltado(w);
    }
    gdk_drag_status(c, dest ? GDK_ACTION_COPY : 0, t);
    if (fila) gtk_tree_path_free(fila);
    g_free(dest);
    return TRUE;
}

static void on_dnd_salir(GtkWidget *w, GdkDragContext *c, guint t, gpointer datos) {
    (void)c; (void)t; (void)datos;
    quitar_resaltado(w);
}

static gboolean on_dnd_soltar(GtkWidget *w, GdkDragContext *c, gint x, gint y, guint t, gpointer datos) {
    (void)x; (void)y; (void)datos;
    gtk_drag_get_data(w, c, gdk_atom_intern_static_string("PAWOS_ITEM"), t);
    return TRUE;
}

static void on_dnd_recibido(GtkWidget *w, GdkDragContext *c, gint x, gint y,
                            GtkSelectionData *sd, guint info, guint t, gpointer datos) {
    (void)sd; (void)info;
    ContextoApp *ctx = datos;
    quitar_resaltado(w);
    gchar *dest = destino_para(ctx, w, x, y, NULL);
    gtk_drag_finish(c, dest != NULL, FALSE, t);
    if (dest) mover_a(ctx, dest);
    g_free(dest);
}

static void configurar_destino_dnd(ContextoApp *ctx, GtkWidget *w) {
    gtk_drag_dest_set(w, 0, TARGETS_MOVER, 1, GDK_ACTION_COPY);
    g_signal_connect(w, "drag-motion", G_CALLBACK(on_dnd_motion), ctx);
    g_signal_connect(w, "drag-leave", G_CALLBACK(on_dnd_salir), ctx);
    g_signal_connect(w, "drag-drop", G_CALLBACK(on_dnd_soltar), ctx);
    g_signal_connect(w, "drag-data-received", G_CALLBACK(on_dnd_recibido), ctx);
}

/* ---------- Respaldo ----------
 * Respaldo de los datos del SQL Server (SmarterASP): cada tabla se
 * convierte a CSV, se guarda un archivo por tabla en la categoria
 * Backups y, ademas, una copia en la tabla "respaldos" del propio
 * SQL Server. Las contrasenas y fotos de clientes NO se incluyen. */

static void csv_texto(GString *g, const char *t) {
    g_string_append_c(g, '"');
    for (const char *p = t; *p; p++) {
        if (*p == '"') g_string_append(g, "\"\"");
        else g_string_append_c(g, *p);
    }
    g_string_append_c(g, '"');
}

static void csv_decimal(GString *g, double valor) {
    char buf[G_ASCII_DTOSTR_BUF_SIZE];
    g_ascii_formatd(buf, sizeof(buf), "%.2f", valor);
    g_string_append(g, buf);
}

static GString *csv_mascotas(void) {
    Mascota *l = NULL; int n = 0;
    if (mascota_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,nombre,especie,raza,edad,estado,fecha_ingreso\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,", l[i].id);
        csv_texto(g, l[i].nombre); g_string_append_c(g, ',');
        csv_texto(g, l[i].especie); g_string_append_c(g, ',');
        csv_texto(g, l[i].raza); g_string_append_c(g, ',');
        g_string_append_printf(g, "%d,", l[i].edad);
        csv_texto(g, l[i].estado); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha_ingreso); g_string_append_c(g, '\n');
    }
    free(l);
    return g;
}

static GString *csv_vacunas(void) {
    Vacuna *l = NULL; int n = 0;
    if (vacuna_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,mascota_id,nombre_vacuna,fecha_aplicacion,fecha_proxima,observaciones,cliente_id\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,%d,", l[i].id, l[i].mascota_id);
        csv_texto(g, l[i].nombre_vacuna); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha_aplicacion); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha_proxima); g_string_append_c(g, ',');
        csv_texto(g, l[i].observaciones);
        g_string_append_printf(g, ",%d\n", l[i].cliente_id);
    }
    free(l);
    return g;
}

static GString *csv_adopciones(void) {
    Adopcion *l = NULL; int n = 0;
    if (adopcion_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,mascota_id,adoptante_nombre,adoptante_contacto,fecha_adopcion\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,%d,", l[i].id, l[i].mascota_id);
        csv_texto(g, l[i].adoptante_nombre); g_string_append_c(g, ',');
        csv_texto(g, l[i].adoptante_contacto); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha_adopcion); g_string_append_c(g, '\n');
    }
    free(l);
    return g;
}

static GString *csv_donantes(void) {
    Donante *l = NULL; int n = 0;
    if (donante_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,nombre,contacto,monto,fecha\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,", l[i].id);
        csv_texto(g, l[i].nombre); g_string_append_c(g, ',');
        csv_texto(g, l[i].contacto); g_string_append_c(g, ',');
        csv_decimal(g, l[i].monto); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha); g_string_append_c(g, '\n');
    }
    free(l);
    return g;
}

static GString *csv_alertas(void) {
    Alerta *l = NULL; int n = 0;
    if (alerta_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,animal_id,tipo,detalle,valor,fecha_hora,atendida\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,", l[i].id);
        csv_texto(g, l[i].animal_id); g_string_append_c(g, ',');
        csv_texto(g, l[i].tipo); g_string_append_c(g, ',');
        csv_texto(g, l[i].detalle); g_string_append_c(g, ',');
        csv_decimal(g, l[i].valor); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha_hora);
        g_string_append_printf(g, ",%d\n", l[i].atendida);
    }
    free(l);
    return g;
}

static GString *csv_clientes(void) {
    Cliente *l = NULL; int n = 0;
    if (cliente_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,correo,nombre,telefono,rol\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,", l[i].id);
        csv_texto(g, l[i].correo); g_string_append_c(g, ',');
        csv_texto(g, l[i].nombre); g_string_append_c(g, ',');
        csv_texto(g, l[i].telefono);
        g_string_append_printf(g, ",%d\n", (int)l[i].rol);
    }
    free(l);
    return g;
}

static GString *csv_notas(void) {
    NotaVeterinario *l = NULL; int n = 0;
    if (nota_veterinario_listar(&l, &n) != 0) return NULL;
    GString *g = g_string_new("id,mascota_id,nota,autor,fecha\n");
    for (int i = 0; i < n; i++) {
        g_string_append_printf(g, "%d,%d,", l[i].id, l[i].mascota_id);
        csv_texto(g, l[i].nota); g_string_append_c(g, ',');
        csv_texto(g, l[i].autor); g_string_append_c(g, ',');
        csv_texto(g, l[i].fecha); g_string_append_c(g, '\n');
    }
    free(l);
    return g;
}

typedef GString *(*FuncionCsv)(void);
typedef struct {
    const char *tabla;
    FuncionCsv  generar;
} TablaRespaldo;

static const TablaRespaldo TABLAS_RESPALDO[] = {
    { "mascotas", csv_mascotas },
    { "vacunas", csv_vacunas },
    { "adopciones", csv_adopciones },
    { "donantes", csv_donantes },
    { "alertas_sensores", csv_alertas },
    { "clientes", csv_clientes },
    { "notas_veterinario", csv_notas }
};
#define N_TABLAS_RESPALDO ((int)(sizeof(TABLAS_RESPALDO) / sizeof(TABLAS_RESPALDO[0])))

/* Validacion en vivo del nombre mientras se escribe (como en la contrasena):
 * avisa si ya existe en tu PC, si ya existe en SmarterASP, o si esta libre. */
typedef struct {
    GtkWidget *dialogo;
    GtkWidget *lbl;
    char     **nubes;      /* nombres que ya estan en SmarterASP (puede ser NULL) */
    int        n_nubes;
    gboolean   validar_nube;
} EstadoNombre;

static void on_nombre_respaldo_cambiado(GtkEditable *editable, gpointer datos) {
    EstadoNombre *e = datos;
    gchar *nombre = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(editable))));
    const char *color = NULL, *texto = NULL;
    gboolean ok = TRUE;

    if (nombre[0] == '\0') {
        texto = NULL;
    } else if (strchr(nombre, '/') || strchr(nombre, '\\')) {
        color = "#C0392B"; texto = "El nombre no puede contener / ni \\."; ok = FALSE;
    } else {
        gchar *completa = g_build_filename(archivos_ruta_base(), "backups", nombre, NULL);
        gboolean local = g_file_test(completa, G_FILE_TEST_EXISTS);
        g_free(completa);
        gboolean nube = FALSE;
        if (e->validar_nube) {
            for (int i = 0; i < e->n_nubes; i++) {
                if (strcmp(e->nubes[i], nombre) == 0) { nube = TRUE; break; }
            }
        }
        if (local) {
            color = "#C0392B"; texto = "Ya existe una carpeta con ese nombre en tu PC."; ok = FALSE;
        } else if (nube) {
            color = "#D68910";
            texto = "Ya existe un respaldo con ese nombre en SmarterASP. Al respaldar podras reemplazarlo.";
        } else {
            color = "#1E8449"; texto = "Nombre disponible.";
        }
    }

    if (texto) {
        gchar *markup = g_markup_printf_escaped("<span size='small' foreground='%s'>%s</span>", color, texto);
        gtk_label_set_markup(GTK_LABEL(e->lbl), markup);
        g_free(markup);
        gtk_widget_set_no_show_all(e->lbl, FALSE);
        gtk_widget_show(e->lbl);
    } else {
        gtk_widget_hide(e->lbl);
    }
    gtk_dialog_set_response_sensitive(GTK_DIALOG(e->dialogo), GTK_RESPONSE_OK, ok);
    g_free(nombre);
}

/* Pide el nombre de la carpeta del respaldo (viene con fecha y hora por
 * defecto) y la crea dentro de Backups. Devuelve FALSE si se cancela. */
static gboolean pedir_carpeta_respaldo(ContextoApp *ctx, const char *sugerido, char *salida, size_t tam,
                                       gboolean validar_nube, gboolean *reemplazar) {
    if (reemplazar) *reemplazar = FALSE;
    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Respaldar datos", GTK_WINDOW(ctx->ventana),
        GTK_DIALOG_MODAL, "_Cancelar", GTK_RESPONSE_CANCEL, "_Respaldar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 420, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);

    GtkWidget *lbl = gtk_label_new("Nombre de la carpeta del respaldo (se crea dentro de Backups):");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);

    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entrada), sugerido);
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);

    GtkWidget *lbl_error = gtk_label_new("");
    gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
    gtk_widget_set_no_show_all(lbl_error, TRUE);
    gtk_box_pack_start(GTK_BOX(area), lbl_error, FALSE, FALSE, 0);

    gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_show_all(dialogo);

    EstadoNombre estado = { dialogo, lbl_error, NULL, 0, validar_nube };
    if (validar_nube) respaldo_listar_nombres(&estado.nubes, &estado.n_nubes);
    g_signal_connect(entrada, "changed", G_CALLBACK(on_nombre_respaldo_cambiado), &estado);
    on_nombre_respaldo_cambiado(GTK_EDITABLE(entrada), &estado);

    gboolean listo = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        gchar *nombre = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        const char *error = NULL;
        if (nombre[0] == '\0') error = "Escribe un nombre para la carpeta.";
        else if (strchr(nombre, '/') || strchr(nombre, '\\')) error = "El nombre no puede contener / ni \\.";
        else if (strcmp(nombre, ".") == 0 || strcmp(nombre, "..") == 0) error = "Ese nombre no es valido.";
        else if (strlen(nombre) >= 100 || strlen(nombre) >= tam) error = "El nombre es demasiado largo.";

        gchar *completa = NULL;
        gboolean quiere_reemplazar = FALSE;
        if (!error) {
            completa = g_build_filename(archivos_ruta_base(), "backups", nombre, NULL);
            if (g_file_test(completa, G_FILE_TEST_EXISTS)) {
                error = "Ya existe una carpeta con ese nombre. Elige otro.";
            } else {
                /* Respaldo de datos: tambien se revisa que el nombre no
                 * exista ya en SmarterASP (evita duplicados y gasto de espacio). */
                if (validar_nube && respaldo_existe_nombre(nombre) == 1) {
                    GtkWidget *aviso = gtk_message_dialog_new(GTK_WINDOW(dialogo), GTK_DIALOG_MODAL,
                        GTK_MESSAGE_WARNING, GTK_BUTTONS_NONE,
                        "Ya existe un respaldo con el nombre \"%s\" en SmarterASP.\n\n"
                        "Si lo reemplazas, se borra el anterior de la nube y se sube este "
                        "(asi no se duplica ni se gasta espacio de mas).", nombre);
                    gtk_dialog_add_buttons(GTK_DIALOG(aviso), "Elegir otro nombre", 1, "Reemplazar", 2, NULL);
                    int resp = gtk_dialog_run(GTK_DIALOG(aviso));
                    gtk_widget_destroy(aviso);
                    if (resp == 2) quiere_reemplazar = TRUE;
                    else error = "Ese nombre ya existe en la nube. Elige otro.";
                }
                if (!error && g_mkdir(completa, 0770) != 0)
                    error = "No se pudo crear la carpeta (revisa los permisos).";
            }
        }
        g_free(completa);

        if (error) {
            gchar *markup = g_markup_printf_escaped("<span size='small' foreground='#C0392B'>%s</span>", error);
            gtk_label_set_markup(GTK_LABEL(lbl_error), markup);
            g_free(markup);
            gtk_widget_set_no_show_all(lbl_error, FALSE);
            gtk_widget_show(lbl_error);
            g_free(nombre);
            continue;
        }
        snprintf(salida, tam, "%s", nombre);
        g_free(nombre);
        if (reemplazar) *reemplazar = quiere_reemplazar;
        listo = TRUE;
        break;
    }
    gtk_widget_destroy(dialogo);
    for (int i = 0; i < estado.n_nubes; i++) free(estado.nubes[i]);
    free(estado.nubes);
    return listo;
}

/* Si hay exactamente una carpeta marcada en la raiz de Backups, devuelve
 * (g_free) su nombre; si no, NULL. */
static gchar *carpeta_marcada_en_backups(ContextoApp *ctx) {
    gchar *cat = categoria_seleccionada(ctx);
    gboolean en_backups = cat && strcmp(cat, "backups") == 0 && ctx->subruta[0] == '\0';
    g_free(cat);
    if (!en_backups) return NULL;
    if (gtk_tree_selection_count_selected_rows(ctx->sel_arch) != 1) return NULL;

    GtkTreeModel *modelo = NULL;
    GList *filas = gtk_tree_selection_get_selected_rows(ctx->sel_arch, &modelo);
    gchar *nombre = NULL;
    gboolean es_dir = FALSE;
    GtkTreeIter iter;
    if (filas && gtk_tree_model_get_iter(modelo, &iter, filas->data))
        gtk_tree_model_get(modelo, &iter, COL_A_NOMBRE, &nombre, COL_A_ES_DIR, &es_dir, -1);
    g_list_free_full(filas, (GDestroyNotify)gtk_tree_path_free);
    if (!es_dir) { g_free(nombre); return NULL; }
    return nombre;
}

static void on_respaldar_clicked(GtkButton *btn, gpointer datos) {
    ContextoApp *ctx = datos;

    char sello[32], fecha_texto[24], sugerido[64], carpeta[128];
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(sello, sizeof(sello), "%Y%m%d_%H%M%S", &tmv);
    strftime(fecha_texto, sizeof(fecha_texto), "%Y-%m-%d %H:%M:%S", &tmv);
    strftime(sugerido, sizeof(sugerido), "Respaldo_%Y-%m-%d_%H-%M", &tmv);

    gboolean reemplazar = FALSE;
    gboolean ya_elegido = FALSE;

    /* Si hay una carpeta de Backups marcada y ese respaldo ya esta en
     * SmarterASP, se avisa antes de hacer nada (evita duplicar). */
    gchar *marcada = carpeta_marcada_en_backups(ctx);
    if (marcada && respaldo_existe_nombre(marcada) == 1) {
        GtkWidget *aviso = gtk_message_dialog_new(GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
            GTK_MESSAGE_WARNING, GTK_BUTTONS_NONE,
            "El respaldo \"%s\" ya existe en SmarterASP.\n\n"
            "Puedes actualizarlo con los datos de ahora (se reemplaza el anterior, no se duplica) "
            "o crear un respaldo nuevo con otro nombre.", marcada);
        gtk_dialog_add_buttons(GTK_DIALOG(aviso), "Cancelar", GTK_RESPONSE_CANCEL,
            "Crear uno nuevo", 1, "Actualizar ese respaldo", 2, NULL);
        int resp = gtk_dialog_run(GTK_DIALOG(aviso));
        gtk_widget_destroy(aviso);
        if (resp == 2) {
            snprintf(carpeta, sizeof(carpeta), "%s", marcada);
            reemplazar = TRUE;
            ya_elegido = TRUE;
        } else if (resp != 1) {
            g_free(marcada);
            return;
        }
    }
    g_free(marcada);

    if (!ya_elegido && !pedir_carpeta_respaldo(ctx, sugerido, carpeta, sizeof(carpeta), TRUE, &reemplazar)) return;

    if (btn) gtk_widget_set_sensitive(GTK_WIDGET(btn), FALSE);
    while (gtk_events_pending()) gtk_main_iteration();

    /* 1. Leer todas las tablas del SQL Server. Si alguna falla, no se
     * guarda nada a medias. */
    GString *csvs[N_TABLAS_RESPALDO];
    const char *fallo = NULL;
    int leidas = 0;
    for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
        csvs[i] = TABLAS_RESPALDO[i].generar();
        if (!csvs[i]) { fallo = TABLAS_RESPALDO[i].tabla; break; }
        leidas++;
    }
    if (fallo) {
        for (int i = 0; i < leidas; i++) g_string_free(csvs[i], TRUE);
        gchar *msg = g_strdup_printf(
            "No se pudo leer la tabla \"%s\" del SQL Server. Revisa la conexion e intenta de nuevo.", fallo);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
        g_free(msg);
        if (btn) gtk_widget_set_sensitive(GTK_WIDGET(btn), TRUE);
        return;
    }

    /* 2. CSV local en la categoria Backups + copia en SmarterASP. */
    /* Si se eligio "Reemplazar", se quita de la nube el respaldo anterior
     * con ese nombre justo antes de subir el nuevo. */
    if (reemplazar) respaldo_borrar_nombre(carpeta);

    int locales = 0, remotos = 0;
    for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
        (void)sello;
        gchar *nombre = g_strdup_printf("%s.csv", TABLAS_RESPALDO[i].tabla);
        gchar *ruta = g_build_filename(archivos_ruta_base(), "backups", carpeta, nombre, NULL);
        if (g_file_set_contents(ruta, csvs[i]->str, (gssize)csvs[i]->len, NULL)) locales++;
        g_free(ruta);
        g_free(nombre);
        if (respaldo_guardar(fecha_texto, carpeta, TABLAS_RESPALDO[i].tabla, csvs[i]->str) == 0) remotos++;
        g_string_free(csvs[i], TRUE);
    }

    /* 2b. Fotos de las mascotas (archivos .jpg) junto a los CSV */
    int fotos_exportadas = 0;
    {
        gchar *dir_fotos = g_build_filename(archivos_ruta_base(), "backups", carpeta, "fotos_mascotas", NULL);
        fotos_exportadas = exportar_fotos_mascotas(dir_fotos);
        g_free(dir_fotos);
    }

    /* 3. Copia del SQLite local (usuarios del personal), como antes. */
    int sqlite_ok = (archivos_respaldar_bd_auto() == 0);

    cargar_categorias(ctx);

    GString *msg = g_string_new("Respaldo terminado.\n\n");
    g_string_append_printf(msg, "- Archivos CSV en Backups/%s: %d de %d\n", carpeta, locales, N_TABLAS_RESPALDO);
    if (fotos_exportadas >= 0)
        g_string_append_printf(msg, "- Fotos de mascotas (Backups/%s/fotos_mascotas): %d\n", carpeta, fotos_exportadas);
    g_string_append_printf(msg, "- Copia en SmarterASP (tabla respaldos): %d de %d\n", remotos, N_TABLAS_RESPALDO);
    g_string_append_printf(msg, "- Base local de usuarios (SQLite): %s", sqlite_ok ? "copiada" : "no se pudo copiar");
    if (remotos < N_TABLAS_RESPALDO) {
        g_string_append(msg, "\n\nSi la copia en SmarterASP salio en 0, revisa que exista la tabla \"respaldos\".");
    }
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg->str,
        locales < N_TABLAS_RESPALDO && remotos < N_TABLAS_RESPALDO);
    g_string_free(msg, TRUE);
    if (btn) gtk_widget_set_sensitive(GTK_WIDGET(btn), TRUE);
}

/* ---------- Respaldo de una carpeta con archivos ----------
 * Copia una carpeta completa (fotos, documentos, subcarpetas) a
 * Backups/<nombre>/<carpeta>. Si hay una carpeta marcada en la lista se
 * respalda esa; si no hay nada marcado, la carpeta que esta abierta. */

typedef struct {
    int     archivos;
    int     fallidos;
    gint64  bytes;
} ResultadoCopia;

static void copiar_recursivo(const char *origen, const char *destino, ResultadoCopia *res) {
    if (g_mkdir_with_parents(destino, 0770) != 0) { res->fallidos++; return; }
    GDir *d = g_dir_open(origen, 0, NULL);
    if (!d) { res->fallidos++; return; }
    const char *nombre;
    while ((nombre = g_dir_read_name(d)) != NULL) {
        gchar *o = g_build_filename(origen, nombre, NULL);
        gchar *dst = g_build_filename(destino, nombre, NULL);
        GStatBuf st;
        if (g_stat(o, &st) != 0) {
            res->fallidos++;
        } else if (S_ISDIR(st.st_mode)) {
            copiar_recursivo(o, dst, res);
        } else {
            GFile *fo = g_file_new_for_path(o);
            GFile *fd = g_file_new_for_path(dst);
            if (g_file_copy(fo, fd, G_FILE_COPY_NONE, NULL, NULL, NULL, NULL)) {
                res->archivos++;
                res->bytes += (gint64)st.st_size;
            } else {
                res->fallidos++;
            }
            g_object_unref(fo);
            g_object_unref(fd);
        }
        g_free(o);
        g_free(dst);
    }
    g_dir_close(d);
}

static void on_respaldar_carpeta_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    gchar *cat = categoria_seleccionada(ctx);
    if (!cat) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Elige primero una categoria a la izquierda.", TRUE);
        return;
    }
    if (strcmp(cat, "backups") == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "Backups ya guarda tus respaldos. Elige otra categoria para respaldarla.", TRUE);
        g_free(cat);
        return;
    }

    gchar *rel_actual = ruta_relativa_actual(ctx, cat);
    gchar *rel_objetivo = NULL;
    gchar *etiqueta = NULL;
    GPtrArray *sel = archivos_seleccionados(ctx);

    if (sel->len == 0) {
        /* Nada marcado: se respalda la carpeta abierta */
        rel_objetivo = g_strdup(rel_actual);
        etiqueta = g_path_get_basename(rel_actual);
    } else {
        gboolean una_carpeta = FALSE;
        if (sel->len == 1) {
            gchar *abs = g_build_filename(archivos_ruta_base(), rel_actual,
                (const char *)g_ptr_array_index(sel, 0), NULL);
            una_carpeta = g_file_test(abs, G_FILE_TEST_IS_DIR);
            g_free(abs);
        }
        if (!una_carpeta) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                "Marca una sola carpeta para respaldarla, o quita la seleccion "
                "(clic en un espacio vacio) para respaldar la carpeta abierta.", TRUE);
            g_ptr_array_free(sel, TRUE);
            g_free(rel_actual);
            g_free(cat);
            return;
        }
        etiqueta = g_strdup(g_ptr_array_index(sel, 0));
        rel_objetivo = g_build_filename(rel_actual, etiqueta, NULL);
    }
    g_ptr_array_free(sel, TRUE);

    char fecha[32], sugerido[128], carpeta[128];
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(fecha, sizeof(fecha), "%Y-%m-%d_%H-%M", &tmv);
    snprintf(sugerido, sizeof(sugerido), "%.60s_%s", etiqueta, fecha);

    if (pedir_carpeta_respaldo(ctx, sugerido, carpeta, sizeof(carpeta), FALSE, NULL)) {
        gchar *origen = g_build_filename(archivos_ruta_base(), rel_objetivo, NULL);
        gchar *destino = g_build_filename(archivos_ruta_base(), "backups", carpeta, etiqueta, NULL);

        ResultadoCopia res = {0, 0, 0};
        copiar_recursivo(origen, destino, &res);

        gchar *tam = g_format_size((guint64)res.bytes);
        gchar *msg;
        if (res.archivos == 0 && res.fallidos == 0)
            msg = g_strdup_printf("La carpeta \"%s\" estaba vacia. Se creo Backups/%s/%s sin archivos.",
                etiqueta, carpeta, etiqueta);
        else
            msg = g_strdup_printf("Respaldo terminado.\n\n- Carpeta: %s\n- Guardado en: Backups/%s/%s\n"
                "- Archivos copiados: %d (%s)\n- Con error: %d",
                etiqueta, carpeta, etiqueta, res.archivos, tam, res.fallidos);
        cargar_categorias(ctx);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, res.fallidos > 0 && res.archivos == 0);
        g_free(msg);
        g_free(tam);
        g_free(origen);
        g_free(destino);
    }

    g_free(etiqueta);
    g_free(rel_objetivo);
    g_free(rel_actual);
    g_free(cat);
}

/* ---------- Integridad de donantes ---------- */

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

/* Columna "Nombre" con un icono (carpeta o archivo) a la izquierda. */
static GtkTreeViewColumn *columna_nombre_con_icono(void) {
    GtkTreeViewColumn *col = gtk_tree_view_column_new();
    gtk_tree_view_column_set_title(col, "Nombre");
    GtkCellRenderer *r_icono = gtk_cell_renderer_pixbuf_new();
    gtk_tree_view_column_pack_start(col, r_icono, FALSE);
    gtk_tree_view_column_add_attribute(col, r_icono, "icon-name", COL_A_ICONO);
    GtkCellRenderer *r_texto = gtk_cell_renderer_text_new();
    gtk_tree_view_column_pack_start(col, r_texto, TRUE);
    gtk_tree_view_column_add_attribute(col, r_texto, "text", COL_A_NOMBRE);
    gtk_tree_view_column_set_resizable(col, TRUE);
    gtk_tree_view_column_set_expand(col, TRUE);
    gtk_tree_view_column_set_sort_column_id(col, COL_A_NOMBRE);
    return col;
}

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Archivos");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 1000, 620);
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
    /* Todo el contenido va dentro de un scroll: si la ventana es chica,
     * aparecen las barras; si es grande, no se muestran. */
    GtkWidget *scroll_ventana = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_ventana), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_overlay_scrolling(GTK_SCROLLED_WINDOW(scroll_ventana), FALSE);
    gtk_container_add(GTK_CONTAINER(scroll_ventana), contenido);
    gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_ventana, TRUE, TRUE, 0);

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
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_cat), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_overlay_scrolling(GTK_SCROLLED_WINDOW(scroll_cat), FALSE);
    gtk_scrolled_window_set_min_content_height(GTK_SCROLLED_WINDOW(scroll_cat), 180);
    gtk_container_add(GTK_CONTAINER(scroll_cat), vista_cat);
    gtk_box_pack_start(GTK_BOX(tarjeta_cat), scroll_cat, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(principal), tarjeta_cat, FALSE, FALSE, 0);

    /* Derecha: barra de acciones + tabla de archivos */
    GtkWidget *derecha = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_box_pack_start(GTK_BOX(principal), derecha, TRUE, TRUE, 0);

    GtkWidget *barra = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);

    ctx->btn_atras = gtk_button_new_with_label("Atras");
    gtk_widget_set_sensitive(ctx->btn_atras, FALSE);
    g_signal_connect(ctx->btn_atras, "clicked", G_CALLBACK(on_atras_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), ctx->btn_atras, FALSE, FALSE, 0);

    ctx->lbl_titulo_cat = gtk_label_new("");
    gtk_widget_set_halign(ctx->lbl_titulo_cat, GTK_ALIGN_START);
    gtk_widget_set_hexpand(ctx->lbl_titulo_cat, TRUE);
    gtk_box_pack_start(GTK_BOX(barra), ctx->lbl_titulo_cat, TRUE, TRUE, 0);

    GtkWidget *btn_agregar = gtk_button_new_with_label("Agregar archivo");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_agregar), "pawos-accion");
    g_signal_connect(btn_agregar, "clicked", G_CALLBACK(on_agregar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_agregar, FALSE, FALSE, 0);

    GtkWidget *btn_nueva = gtk_button_new_with_label("Nueva carpeta");
    g_signal_connect(btn_nueva, "clicked", G_CALLBACK(on_nueva_carpeta_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_nueva, FALSE, FALSE, 0);

    GtkWidget *btn_todo = gtk_button_new_with_label("Seleccionar todo");
    g_signal_connect(btn_todo, "clicked", G_CALLBACK(on_seleccionar_todo_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_todo, FALSE, FALSE, 0);

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
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_INT64, G_TYPE_STRING, G_TYPE_BOOLEAN, G_TYPE_STRING);
    GtkWidget *vista_arch = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_arch));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_nombre_con_icono());
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_texto("Tamano", COL_A_TAM, COL_A_BYTES, FALSE));
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), columna_texto("Modificado", COL_A_FECHA, COL_A_FECHA, FALSE));
    ctx->col_nube = columna_texto("En la nube", COL_A_NUBE, COL_A_NUBE, FALSE);
    gtk_tree_view_column_set_visible(ctx->col_nube, FALSE);
    gtk_tree_view_append_column(GTK_TREE_VIEW(vista_arch), ctx->col_nube);
    ctx->sel_arch = gtk_tree_view_get_selection(GTK_TREE_VIEW(vista_arch));
    gtk_tree_selection_set_mode(ctx->sel_arch, GTK_SELECTION_MULTIPLE);
    gtk_tree_view_set_rubber_banding(GTK_TREE_VIEW(vista_arch), TRUE);
    g_signal_connect(vista_arch, "button-press-event", G_CALLBACK(on_lista_clic), ctx);
    g_signal_connect(vista_arch, "button-release-event", G_CALLBACK(on_lista_soltar), ctx);
    g_signal_connect(vista_arch, "key-press-event", G_CALLBACK(on_lista_tecla), ctx);
    gtk_tree_selection_set_select_function(ctx->sel_arch, permitir_cambio_seleccion, ctx, NULL);
    g_signal_connect(vista_arch, "row-activated", G_CALLBACK(on_archivo_activado), ctx);

    /* Arrastrar y soltar para mover */
    ctx->vista_arch = vista_arch;
    ctx->vista_cat = vista_cat;
    gtk_tree_view_enable_model_drag_source(GTK_TREE_VIEW(vista_arch), GDK_BUTTON1_MASK,
        TARGETS_MOVER, 1, GDK_ACTION_COPY);
    g_signal_connect(vista_arch, "drag-begin", G_CALLBACK(on_arrastre_inicio), ctx);
    g_signal_connect(vista_arch, "drag-data-get", G_CALLBACK(on_arrastre_datos), ctx);
    configurar_destino_dnd(ctx, vista_arch);
    configurar_destino_dnd(ctx, vista_cat);
    configurar_destino_dnd(ctx, ctx->btn_atras);

    GtkWidget *scroll_arch = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_arch), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_overlay_scrolling(GTK_SCROLLED_WINDOW(scroll_arch), FALSE);
    gtk_scrolled_window_set_min_content_height(GTK_SCROLLED_WINDOW(scroll_arch), 180);
    gtk_widget_set_vexpand(scroll_arch, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll_arch), vista_arch);

    /* Mensaje centrado sobre la lista cuando la carpeta no tiene nada */
    GtkWidget *superpuesto = gtk_overlay_new();
    gtk_container_add(GTK_CONTAINER(superpuesto), scroll_arch);
    ctx->lbl_vacio = gtk_label_new(NULL);
    gtk_label_set_justify(GTK_LABEL(ctx->lbl_vacio), GTK_JUSTIFY_CENTER);
    gtk_label_set_markup(GTK_LABEL(ctx->lbl_vacio),
        "<span size='x-large' weight='bold' foreground='#7F8C8D'>Esta carpeta esta vacia</span>\n"
        "<span foreground='#95A5A6'>Usa \"Agregar archivo\" o \"Nueva carpeta\",\n"
        "o arrastra aqui elementos desde otra carpeta.</span>");
    gtk_widget_set_halign(ctx->lbl_vacio, GTK_ALIGN_CENTER);
    gtk_widget_set_valign(ctx->lbl_vacio, GTK_ALIGN_CENTER);
    gtk_widget_set_no_show_all(ctx->lbl_vacio, TRUE);
    gtk_widget_set_visible(ctx->lbl_vacio, FALSE);
    gtk_overlay_add_overlay(GTK_OVERLAY(superpuesto), ctx->lbl_vacio);
    gtk_overlay_set_overlay_pass_through(GTK_OVERLAY(superpuesto), ctx->lbl_vacio, TRUE);
    gtk_box_pack_start(GTK_BOX(tarjeta_arch), superpuesto, TRUE, TRUE, 0);
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

    GtkWidget *btn_respaldar = gtk_button_new_with_label("Respaldar datos ahora");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_respaldar), "pawos-accion");
    g_signal_connect(btn_respaldar, "clicked", G_CALLBACK(on_respaldar_clicked), ctx);
    GtkWidget *btn_resp_carpeta = gtk_button_new_with_label("Respaldar carpeta");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_resp_carpeta), "pawos-accion");
    g_signal_connect(btn_resp_carpeta, "clicked", G_CALLBACK(on_respaldar_carpeta_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(fila_inferior), btn_resp_carpeta, FALSE, FALSE, 0);
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
