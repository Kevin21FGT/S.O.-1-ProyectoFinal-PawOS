#!/usr/bin/env python3
"""
parche-vacunas-clic-derecho.py

Refugio GUI -> Agenda de Vacunas: clic derecho sobre una vacuna con
"Editar" y "Eliminar" (sin botones nuevos). Editar permite cambiar nombre,
fecha de aplicacion, proxima dosis y observaciones. Solo Admin y
Veterinario (igual que Registrar vacuna).

Uso (parado en la raiz del repo):
    python3 parche-vacunas-clic-derecho.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "static gboolean on_vacunas_clic("

ANCLA_FUNC = "static void abrir_pantalla_vacunas(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {"
NUEVO_FUNC = r"""/* ---- Clic derecho en la lista de vacunas: Editar / Eliminar ---- */
static void editar_vacuna_id(ContextoVacunas *ctx, int id) {
    Vacuna v;
    memset(&v, 0, sizeof(v));
    if (vacuna_buscar_por_id(id, &v) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer esa vacuna.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar vacuna", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
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
    gtk_entry_set_text(GTK_ENTRY(e_nombre), v.nombre_vacuna);
    gtk_entry_set_text(GTK_ENTRY(e_aplic), v.fecha_aplicacion);
    gtk_entry_set_text(GTK_ENTRY(e_prox), v.fecha_proxima);
    gtk_entry_set_text(GTK_ENTRY(e_obs), v.observaciones);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_aplic), "AAAA-MM-DD");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_prox), "AAAA-MM-DD (opcional)");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre de la vacuna:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Fecha de aplicacion:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_aplic, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Proxima dosis:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_prox, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Observaciones:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_obs, 1, 3, 1, 1);
    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    gtk_widget_show_all(dialogo);

    gboolean ok = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;
        const char *nom = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *fapl = gtk_entry_get_text(GTK_ENTRY(e_aplic));
        const char *fprox = gtk_entry_get_text(GTK_ENTRY(e_prox));
        if (nom[0] == '\0') {
            mostrar_mensaje(GTK_WINDOW(dialogo), "El nombre de la vacuna no puede quedar vacio.", TRUE);
            continue;
        }
        if (!fecha_valida(fapl)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La fecha de aplicacion debe tener el formato AAAA-MM-DD y ser una fecha valida.", TRUE);
            continue;
        }
        if (fprox[0] != '\0' && !fecha_valida(fprox)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La proxima dosis debe tener el formato AAAA-MM-DD, o dejarse vacia.", TRUE);
            continue;
        }
        ok = TRUE;
        break;
    }

    if (ok) {
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));
        if (vacuna_actualizar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna actualizada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar la vacuna.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void eliminar_vacuna_id(ContextoVacunas *ctx, int id) {
    GtkWidget *conf = gtk_message_dialog_new(
        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
        GTK_BUTTONS_YES_NO, "Eliminar esta vacuna del registro?");
    gint r = gtk_dialog_run(GTK_DIALOG(conf));
    gtk_widget_destroy(conf);
    if (r != GTK_RESPONSE_YES) return;
    if (vacuna_eliminar(id) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo eliminar la vacuna.", TRUE);
        return;
    }
    cargar_vacunas(ctx);
}

static void on_vacuna_menu_editar(GtkMenuItem *item, gpointer datos) {
    editar_vacuna_id((ContextoVacunas *)datos,
        GPOINTER_TO_INT(g_object_get_data(G_OBJECT(item), "vacuna-id")));
}

static void on_vacuna_menu_eliminar(GtkMenuItem *item, gpointer datos) {
    eliminar_vacuna_id((ContextoVacunas *)datos,
        GPOINTER_TO_INT(g_object_get_data(G_OBJECT(item), "vacuna-id")));
}

static gboolean on_vacunas_clic(GtkWidget *vista, GdkEventButton *ev, gpointer datos) {
    ContextoVacunas *ctx = (ContextoVacunas *)datos;
    if (ev->type != GDK_BUTTON_PRESS || ev->button != 3) return FALSE;

    GtkTreePath *ruta = NULL;
    if (!gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(vista), (gint)ev->x, (gint)ev->y,
                                       &ruta, NULL, NULL, NULL))
        return FALSE;
    gtk_tree_view_set_cursor(GTK_TREE_VIEW(vista), ruta, NULL, FALSE);

    GtkTreeIter iter;
    int id = -1;
    if (gtk_tree_model_get_iter(GTK_TREE_MODEL(ctx->store), &iter, ruta))
        gtk_tree_model_get(GTK_TREE_MODEL(ctx->store), &iter, COL_V_ID, &id, -1);
    gtk_tree_path_free(ruta);
    if (id < 0) return FALSE;

    if (ctx->rol == ROL_VOLUNTARIO) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Requiere rol Admin o Veterinario.", TRUE);
        return TRUE;
    }

    GtkWidget *menu = gtk_menu_new();
    GtkWidget *it_editar = gtk_menu_item_new_with_label("Editar");
    GtkWidget *it_elim = gtk_menu_item_new_with_label("Eliminar");
    g_object_set_data(G_OBJECT(it_editar), "vacuna-id", GINT_TO_POINTER(id));
    g_object_set_data(G_OBJECT(it_elim), "vacuna-id", GINT_TO_POINTER(id));
    g_signal_connect(it_editar, "activate", G_CALLBACK(on_vacuna_menu_editar), ctx);
    g_signal_connect(it_elim, "activate", G_CALLBACK(on_vacuna_menu_eliminar), ctx);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_editar);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_elim);
    gtk_widget_show_all(menu);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent *)ev);
    return TRUE;
}

static void abrir_pantalla_vacunas(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {"""

ANCLA_CONEXION = """    cargar_vacunas(ctx);
    mostrar_en_panel(area_dinamica, caja);"""
NUEVO_CONEXION = """    g_signal_connect(ctx->treeview, "button-press-event", G_CALLBACK(on_vacunas_clic), ctx);

    cargar_vacunas(ctx);
    mostrar_en_panel(area_dinamica, caja);"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de abrir_pantalla_vacunas"),
    (ANCLA_CONEXION, NUEVO_CONEXION, "carga final del panel de vacunas"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_vacunas_clic")
    print(f"Backup: {ARCHIVO}.bak_vacunas_clic")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
