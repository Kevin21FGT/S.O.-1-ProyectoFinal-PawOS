#!/usr/bin/env python3
"""
parche-clientes-clic-derecho.py

Refugio GUI -> Administrar Clientes: clic derecho sobre un cliente con
"Editar datos" (nombre y telefono; el correo y la contrasena no se tocan)
y "Cambiar rol". El boton "Cambiar rol del seleccionado" se mantiene.

Uso (parado en la raiz del repo):
    python3 parche-clientes-clic-derecho.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "static gboolean on_clientes_clic("

ANCLA_FUNC = "static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {"
NUEVO_FUNC = r"""/* ---- Clic derecho en Administrar Clientes: Editar datos / Cambiar rol ---- */
static void editar_datos_cliente(GtkTreeView *vista) {
    GtkTreeSelection *seleccion = gtk_tree_view_get_selection(vista);
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(seleccion, &modelo, &iter)) return;
    gint id_cliente;
    gtk_tree_model_get(modelo, &iter, 0, &id_cliente, -1);

    /* El telefono no esta en la tabla: se busca en la lista de Clientes. */
    char nombre_actual[64] = "", telefono_actual[32] = "";
    Cliente *lista = NULL;
    int n = 0;
    if (cliente_listar(&lista, &n) == 0) {
        for (int i = 0; i < n; i++) {
            if (lista[i].id == id_cliente) {
                snprintf(nombre_actual, sizeof(nombre_actual), "%s", lista[i].nombre);
                snprintf(telefono_actual, sizeof(telefono_actual), "%s", lista[i].telefono);
                break;
            }
        }
        free(lista);
    }

    GtkWindow *padre = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(vista)));
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar datos del cliente", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 12);
    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_tel = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(e_nombre), nombre_actual);
    gtk_entry_set_text(GTK_ENTRY(e_tel), telefono_actual);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_tel), "Ej: 58381311 (WhatsApp)");
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Telefono:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_tel, 1, 1, 1, 1);
    gtk_container_add(GTK_CONTAINER(area), grid);
    gtk_widget_show_all(dialogo);

    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;
        const char *nom = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *tel = gtk_entry_get_text(GTK_ENTRY(e_tel));
        if (nom[0] == '\0') {
            mostrar_mensaje(GTK_WINDOW(dialogo), "El nombre no puede quedar vacio.", TRUE);
            continue;
        }
        int digitos = 0;
        for (const char *p = tel; *p; p++) if (*p >= '0' && *p <= '9') digitos++;
        if (tel[0] != '\0' && digitos < 8) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "El telefono debe tener minimo 8 digitos.", TRUE);
            continue;
        }
        /* Contrasena vacia = no se cambia. */
        if (cliente_actualizar(id_cliente, nom, "") != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo guardar el nombre.", TRUE);
            continue;
        }
        if (tel[0] != '\0' && strcmp(tel, telefono_actual) != 0
            && cliente_actualizar_telefono(id_cliente, tel) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "Se guardo el nombre, pero no el telefono.", TRUE);
            gtk_list_store_set(GTK_LIST_STORE(modelo), &iter, 1, nom, -1);
            continue;
        }
        gtk_list_store_set(GTK_LIST_STORE(modelo), &iter, 1, nom, -1);
        mostrar_mensaje(GTK_WINDOW(dialogo), "Datos actualizados.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

static void on_clientes_menu_editar(GtkMenuItem *item, gpointer datos) {
    (void)item;
    editar_datos_cliente(GTK_TREE_VIEW(datos));
}

static void on_clientes_menu_rol(GtkMenuItem *item, gpointer datos) {
    (void)item;
    on_cambiar_rol_cliente_clicked(NULL, datos);
}

static gboolean on_clientes_clic(GtkWidget *vista, GdkEventButton *ev, gpointer datos) {
    (void)datos;
    if (ev->type != GDK_BUTTON_PRESS || ev->button != 3) return FALSE;
    GtkTreePath *ruta = NULL;
    if (!gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(vista), (gint)ev->x, (gint)ev->y,
                                       &ruta, NULL, NULL, NULL))
        return FALSE;
    gtk_tree_view_set_cursor(GTK_TREE_VIEW(vista), ruta, NULL, FALSE);
    gtk_tree_path_free(ruta);

    GtkWidget *menu = gtk_menu_new();
    GtkWidget *it_editar = gtk_menu_item_new_with_label("Editar datos");
    GtkWidget *it_rol = gtk_menu_item_new_with_label("Cambiar rol");
    g_signal_connect(it_editar, "activate", G_CALLBACK(on_clientes_menu_editar), vista);
    g_signal_connect(it_rol, "activate", G_CALLBACK(on_clientes_menu_rol), vista);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_editar);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_rol);
    gtk_widget_show_all(menu);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent *)ev);
    return TRUE;
}

static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {"""

ANCLA_CONEXION = """    GtkWidget *btn_cambiar = gtk_button_new_with_label("Cambiar rol del seleccionado");"""
NUEVO_CONEXION = """    g_signal_connect(vista, "button-press-event", G_CALLBACK(on_clientes_clic), NULL);

    GtkWidget *btn_cambiar = gtk_button_new_with_label("Cambiar rol del seleccionado");"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de Administrar Clientes"),
    (ANCLA_CONEXION, NUEVO_CONEXION, "boton Cambiar rol"),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_clientes_clic")
    print(f"Backup: {ARCHIVO}.bak_clientes_clic")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
