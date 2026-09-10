#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Administrar Colaboradores" de ventana emergente a panel
embebido. No toca cargar_colaboradores(), on_agregar_colaborador_clicked,
ni la restriccion de "solo Admin" (que aqui vive dentro de la propia
funcion abrir_pantalla_administrar_colaboradores, a diferencia de otros
modulos donde esta en el _clicked -- se deja exactamente en el mismo
lugar y con la misma logica).
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_administrar_colaboradores_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_administrar_colaboradores(GTK_WINDOW(d->ventana_principal), d->rol);
}'''

NUEVO_CLICKED = r'''static void on_administrar_colaboradores_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_administrar_colaboradores(d->area_dinamica, d->ventana_principal, d->rol);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_administrar_colaboradores(GtkWindow *padre, Rol rol) {
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

    mostrar_con_fundido(ventana);
}'''

NUEVO_ABRIR = r'''static void abrir_pantalla_administrar_colaboradores(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    if (rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(ventana_principal), "Requiere rol Administrador.", TRUE);
        return;
    }

    ContextoColaboradores *ctx = g_malloc0(sizeof(ContextoColaboradores));

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    ctx->ventana = ventana_principal;
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-colaboradores", ctx, g_free);

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
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    mostrar_en_panel(area_dinamica, caja);
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

    anclas = [("ANCLA_CLICKED", ANCLA_CLICKED), ("ANCLA_ABRIR", ANCLA_ABRIR)]
    for nombre, ancla in anclas:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: {nombre} aparece {n} veces (se esperaba 1). No se modifico nada.")
            sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA_CLICKED, NUEVO_CLICKED).replace(ANCLA_ABRIR, NUEVO_ABRIR)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Administrar Colaboradores ahora se abre embebido en el panel principal")


if __name__ == "__main__":
    main()
