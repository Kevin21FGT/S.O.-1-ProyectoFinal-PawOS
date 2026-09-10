#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Alertas de Sensores" de ventana emergente a panel embebido.
No toca cargar_alertas() ni ninguno de los manejadores (ver pendientes,
ver todas, marcar atendida, registrar de prueba), ni la restriccion de
rol para Voluntario.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_alertas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_alertas(d->ventana_principal, d->rol);
}'''

NUEVO_CLICKED = r'''static void on_alertas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_alertas(d->area_dinamica, d->ventana_principal, d->rol);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_alertas(GtkWidget *padre, Rol rol) {
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
    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void abrir_pantalla_alertas(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    ContextoAlertas *ctx = g_malloc0(sizeof(ContextoAlertas));
    ctx->rol = rol;
    ctx->solo_pendientes = TRUE;
    ctx->ventana = ventana_principal;

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-alertas", ctx, g_free);

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
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    cargar_alertas(ctx);
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
    print("Alertas de Sensores ahora se abre embebido en el panel principal")


if __name__ == "__main__":
    main()
