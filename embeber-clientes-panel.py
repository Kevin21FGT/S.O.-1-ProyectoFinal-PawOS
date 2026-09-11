#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Administrar Clientes" de ventana emergente a panel embebido.
Este modulo no usa un contexto (ContextoX) como los demas -- arma todo
directo dentro de on_administrar_clientes_clicked y no reserva memoria
propia, asi que no hace falta ningun g_object_set_data_full para
limpieza. No se toca cliente_listar(), cliente_rol_nombre(), ni
on_cambiar_rol_cliente_clicked (ese dialogo ya usa NULL como padre, no
depende en nada de si el treeview esta en una ventana o embebido).
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA = r'''static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {
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

    mostrar_con_fundido(ventana);
}'''

NUEVO = r'''static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;
    if (!d || d->rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Solo el Administrador puede administrar Clientes.", TRUE);
        return;
    }

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

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
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), d->area_dinamica);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    mostrar_en_panel(d->area_dinamica, caja);
}'''


def siguiente_backup(ruta: Path) -> Path:
    n = 1
    while True:
        candidato = ruta.with_name(ruta.name + f".bak{n}")
        if not candidato.exists():
            return candidato
        n += 1


def main():
    if not ARCHIVO.exists():
        print(f"ERROR: no se encontro {ARCHIVO}. Ejecuta este script desde la raiz del repo.")
        sys.exit(1)

    contenido = ARCHIVO.read_text(encoding="utf-8")

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el ancla aparece {n} veces (se esperaba 1). No se modifico nada.")
        sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA, NUEVO)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Administrar Clientes ahora se abre embebido en el panel principal")


if __name__ == "__main__":
    main()
