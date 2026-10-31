/*
 * main_vacunas_gui.c - PawOS Vacunas GUI
 *
 * App grafica standalone (GTK3) para la Agenda de Vacunas de PawOS
 * Refugio. Es una de las "apps" propias del sistema operativo PawOS,
 * pensada como utilidad rapida de consulta/registro de vacunas,
 * separada de PawOS Refugio GUI.
 *
 * IMPORTANTE: no reimplementa ninguna logica de negocio. Toda la
 * logica (validaciones, consultas, SQL Server compartido via ODBC,
 * etc.) sigue viviendo en src/db/db.c -- este archivo solo construye
 * la interfaz grafica y llama a las funciones que ya existen
 * (vacuna_agregar, vacuna_listar, vacuna_pendientes, etc.).
 */
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "db/db.h"
#include "version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"

enum {
    COL_ID = 0,
    COL_MASCOTA,
    COL_VACUNA,
    COL_FECHA_APLICACION,
    COL_FECHA_PROXIMA,
    COL_ESTADO,
    COL_COLOR,
    COL_RECORDATORIO,
    COL_OBSERVACIONES,
    N_COLUMNAS
};

typedef struct {
    GtkWidget    *ventana;
    GtkListStore *store;
    GtkWidget    *treeview;
    GtkWidget    *chk_solo_pendientes;
} ContextoApp;

static void hoy_texto(char *buf, size_t len) {
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(buf, len, "%Y-%m-%d", &tmv);
}

static const char *nombre_mascota(int mascota_id) {
    static char buf[80];
    Mascota m;
    if (mascota_buscar_por_id(mascota_id, &m) == 0) {
        snprintf(buf, sizeof(buf), "%s (#%d)", m.nombre, mascota_id);
    } else {
        snprintf(buf, sizeof(buf), "(mascota #%d)", mascota_id);
    }
    return buf;
}

/* Valida que una fecha tenga el formato estricto AAAA-MM-DD y sea una
 * fecha real (dia valido para ese mes/anio, incluyendo anios
 * bisiestos). Se agrega porque las comparaciones de fecha en db.c
 * (vacuna_pendientes) son por texto y solo funcionan bien si TODAS
 * las fechas guardadas usan este mismo formato. */
static gboolean fecha_valida(const char *fecha) {
    if (!fecha || strlen(fecha) != 10) return FALSE;
    if (fecha[4] != '-' || fecha[7] != '-') return FALSE;
    int anio, mes, dia;
    if (sscanf(fecha, "%4d-%2d-%2d", &anio, &mes, &dia) != 3) return FALSE;
    if (mes < 1 || mes > 12) return FALSE;
    if (dia < 1 || dia > 31) return FALSE;
    static const int dias_por_mes[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    int max_dia = dias_por_mes[mes - 1];
    if (mes == 2) {
        gboolean bisiesto = (anio % 4 == 0 && (anio % 100 != 0 || anio % 400 == 0));
        if (bisiesto) max_dia = 29;
    }
    return dia <= max_dia;
}

static void calcular_estado(const char *fecha_proxima, const char *hoy,
                             const char **estado_out, const char **color_out) {
    if (!fecha_proxima || fecha_proxima[0] == '\0') {
        *estado_out = "-";
        *color_out = "#555555";
        return;
    }
    int cmp = strcmp(fecha_proxima, hoy);
    if (cmp < 0) {
        *estado_out = "VENCIDA";
        *color_out = "#C0392B";
    } else if (cmp == 0) {
        *estado_out = "HOY";
        *color_out = "#D68910";
    } else {
        *estado_out = "Al dia";
        *color_out = "#1E8449";
    }
}

static void llenar_store(GtkListStore *store, Vacuna *vs, int n) {
    char hoy[16];
    hoy_texto(hoy, sizeof(hoy));
    gtk_list_store_clear(store);
    for (int i = 0; i < n; i++) {
        const char *estado, *color;
        calcular_estado(vs[i].fecha_proxima, hoy, &estado, &color);
        int enviado = vacuna_recordatorio_enviado(vs[i].id);
        GtkTreeIter iter;
        gtk_list_store_append(store, &iter);
        gtk_list_store_set(store, &iter,
            COL_ID, vs[i].id,
            COL_MASCOTA, nombre_mascota(vs[i].mascota_id),
            COL_VACUNA, vs[i].nombre_vacuna,
            COL_FECHA_APLICACION, vs[i].fecha_aplicacion,
            COL_FECHA_PROXIMA, vs[i].fecha_proxima,
            COL_ESTADO, estado,
            COL_COLOR, color,
            COL_RECORDATORIO, enviado ? "Si" : "No",
            COL_OBSERVACIONES, vs[i].observaciones,
            -1);
    }
}

static void recargar(ContextoApp *ctx) {
    Vacuna *vs;
    int n;
    gboolean solo_pendientes = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(ctx->chk_solo_pendientes));

    int rc = solo_pendientes ? vacuna_pendientes(&vs, &n) : vacuna_listar(&vs, &n);
    if (rc == 0) {
        llenar_store(ctx->store, vs, n);
        free(vs);
    } else {
        gtk_list_store_clear(ctx->store);
    }
}

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

static int obtener_id_seleccionado(GtkWidget *treeview) {
    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(treeview));
    GtkTreeModel *model;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(sel, &model, &iter)) return -1;
    int id;
    gtk_tree_model_get(model, &iter, COL_ID, &id, -1);
    return id;
}

/* Dialogo para registrar o editar una vacuna. Si es_nuevo es TRUE, el
 * campo "ID de mascota" se puede editar; si es FALSE (edicion), queda
 * fijo (no se permite reasignar la vacuna a otra mascota). */
static gboolean dialogo_vacuna(GtkWindow *padre, Vacuna *v_inout, gboolean es_nuevo) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        es_nuevo ? "Registrar vacuna" : "Editar vacuna", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Guardar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 400, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *entry_mascota = gtk_entry_new();
    if (v_inout->mascota_id > 0) {
        char buf_id[16];
        snprintf(buf_id, sizeof(buf_id), "%d", v_inout->mascota_id);
        gtk_entry_set_text(GTK_ENTRY(entry_mascota), buf_id);
    }
    gtk_widget_set_sensitive(entry_mascota, es_nuevo);

    GtkWidget *entry_vacuna = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_vacuna), v_inout->nombre_vacuna);

    GtkWidget *entry_fecha_apl = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_fecha_apl), v_inout->fecha_aplicacion);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_fecha_apl), "AAAA-MM-DD");

    GtkWidget *entry_fecha_prox = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_fecha_prox), v_inout->fecha_proxima);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_fecha_prox), "AAAA-MM-DD (opcional)");

    GtkWidget *entry_obs = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_obs), v_inout->observaciones);

    int fila = 0;
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("ID de mascota:"), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_mascota, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre de la vacuna:"), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_vacuna, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Fecha de aplicacion:"), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_fecha_apl, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Proxima dosis:"), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_fecha_prox, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Observaciones:"), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_obs, 1, fila++, 1, 1);

    gtk_widget_show_all(dialogo);
    gboolean ok = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        const char *fapl = gtk_entry_get_text(GTK_ENTRY(entry_fecha_apl));
        const char *fprox = gtk_entry_get_text(GTK_ENTRY(entry_fecha_prox));

        if (!fecha_valida(fapl)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La fecha de aplicacion debe tener el formato AAAA-MM-DD y ser una fecha valida (ej: 2026-10-16).",
                TRUE);
            continue;
        }
        if (fprox[0] != '\0' && !fecha_valida(fprox)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La proxima dosis debe tener el formato AAAA-MM-DD, o dejarse vacia si no aplica.",
                TRUE);
            continue;
        }

        if (es_nuevo) {
            v_inout->mascota_id = atoi(gtk_entry_get_text(GTK_ENTRY(entry_mascota)));
        }
        snprintf(v_inout->nombre_vacuna, sizeof(v_inout->nombre_vacuna), "%s",
                 gtk_entry_get_text(GTK_ENTRY(entry_vacuna)));
        snprintf(v_inout->fecha_aplicacion, sizeof(v_inout->fecha_aplicacion), "%s", fapl);
        snprintf(v_inout->fecha_proxima, sizeof(v_inout->fecha_proxima), "%s", fprox);
        snprintf(v_inout->observaciones, sizeof(v_inout->observaciones), "%s",
                 gtk_entry_get_text(GTK_ENTRY(entry_obs)));
        ok = TRUE;
        break;
    }
    gtk_widget_destroy(dialogo);
    return ok;
}

static void on_registrar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    Vacuna v;
    memset(&v, 0, sizeof(v));
    if (!dialogo_vacuna(GTK_WINDOW(ctx->ventana), &v, TRUE)) return;

    if (v.mascota_id <= 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "ID de mascota invalido.", TRUE);
        return;
    }
    Mascota chequeo;
    if (mascota_buscar_por_id(v.mascota_id, &chequeo) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No existe una mascota con ese ID.", TRUE);
        return;
    }
    if (vacuna_agregar(&v) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo registrar la vacuna.", TRUE);
        return;
    }
    recargar(ctx);
}

static void on_editar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    int id = obtener_id_seleccionado(ctx->treeview);
    if (id < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona una vacuna de la lista primero.", TRUE);
        return;
    }
    Vacuna v;
    if (vacuna_buscar_por_id(id, &v) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer esa vacuna.", TRUE);
        return;
    }
    if (!dialogo_vacuna(GTK_WINDOW(ctx->ventana), &v, FALSE)) return;

    if (vacuna_actualizar(&v) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar la vacuna.", TRUE);
        return;
    }
    recargar(ctx);
}

static void on_eliminar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    int id = obtener_id_seleccionado(ctx->treeview);
    if (id < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona una vacuna de la lista primero.", TRUE);
        return;
    }
    if (!confirmar(GTK_WINDOW(ctx->ventana), "¿Eliminar esta vacuna del registro?")) return;

    if (vacuna_eliminar(id) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo eliminar la vacuna.", TRUE);
        return;
    }
    recargar(ctx);
}

static void on_marcar_enviado_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    int id = obtener_id_seleccionado(ctx->treeview);
    if (id < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona una vacuna de la lista primero.", TRUE);
        return;
    }
    if (vacuna_marcar_recordatorio_enviado(id) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo marcar el recordatorio.", TRUE);
        return;
    }
    recargar(ctx);
}

static void on_actualizar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    recargar((ContextoApp *)datos);
}

static void on_toggle_pendientes(GtkToggleButton *btn, gpointer datos) {
    (void)btn;
    recargar((ContextoApp *)datos);
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
        "  padding: 16px;"
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

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS Vacunas");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 950, 600);
    gtk_window_set_position(GTK_WINDOW(ctx->ventana), GTK_WIN_POS_CENTER);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    /* Encabezado tipo PawOS Refugio GUI (franja verde de marca). */
    GtkWidget *encabezado = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "pawos-header");
    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf(
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Vacunas</span>  <span size='small'>v%s</span>",
        PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_box_pack_start(GTK_BOX(encabezado), lbl_titulo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), encabezado, FALSE, FALSE, 0);

    /* Barra de herramientas. */
    GtkWidget *barra = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(barra), 14);

    ctx->chk_solo_pendientes = gtk_check_button_new_with_label("Mostrar solo pendientes/vencidas");
    gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(ctx->chk_solo_pendientes), TRUE);
    g_signal_connect(ctx->chk_solo_pendientes, "toggled", G_CALLBACK(on_toggle_pendientes), ctx);
    gtk_box_pack_start(GTK_BOX(barra), ctx->chk_solo_pendientes, FALSE, FALSE, 0);

    GtkWidget *relleno = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
    gtk_widget_set_hexpand(relleno, TRUE);
    gtk_box_pack_start(GTK_BOX(barra), relleno, TRUE, TRUE, 0);

    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar vacuna");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_registrar), "pawos-accion");
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_registrar, FALSE, FALSE, 0);

    GtkWidget *btn_editar = gtk_button_new_with_label("Editar");
    g_signal_connect(btn_editar, "clicked", G_CALLBACK(on_editar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_editar, FALSE, FALSE, 0);

    GtkWidget *btn_marcar = gtk_button_new_with_label("Marcar recordatorio enviado");
    g_signal_connect(btn_marcar, "clicked", G_CALLBACK(on_marcar_enviado_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_marcar, FALSE, FALSE, 0);

    GtkWidget *btn_eliminar = gtk_button_new_with_label("Eliminar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_eliminar), "pawos-peligro");
    g_signal_connect(btn_eliminar, "clicked", G_CALLBACK(on_eliminar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_eliminar, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar");
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra), btn_actualizar, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja_raiz), barra, FALSE, FALSE, 0);

    /* Lista de vacunas, dentro de una tarjeta y con scroll (para que
     * nunca quede contenido invisible sin forma de llegar a el). */
    GtkWidget *panel = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_set_border_width(GTK_CONTAINER(panel), 14);
    gtk_widget_set_vexpand(panel, TRUE);

    GtkWidget *tarjeta = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta), "pawos-tarjeta");
    gtk_widget_set_vexpand(tarjeta, TRUE);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll),
        GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);

    ctx->store = gtk_list_store_new(N_COLUMNAS,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));

    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Mascota", gtk_cell_renderer_text_new(), "text", COL_MASCOTA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Vacuna", gtk_cell_renderer_text_new(), "text", COL_VACUNA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Aplicada", gtk_cell_renderer_text_new(), "text", COL_FECHA_APLICACION, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Proxima dosis", gtk_cell_renderer_text_new(), "text", COL_FECHA_PROXIMA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Estado", gtk_cell_renderer_text_new(), "text", COL_ESTADO, "foreground", COL_COLOR, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Recordatorio enviado", gtk_cell_renderer_text_new(), "text", COL_RECORDATORIO, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->treeview),
        -1, "Observaciones", gtk_cell_renderer_text_new(), "text", COL_OBSERVACIONES, NULL);

    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(tarjeta), scroll, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(panel), tarjeta, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), panel, TRUE, TRUE, 0);

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

    aplicar_estilos_simples();

    ContextoApp ctx;
    memset(&ctx, 0, sizeof(ctx));
    construir_ventana(&ctx);
    recargar(&ctx);

    gtk_main();
    db_close();
    return 0;
}
