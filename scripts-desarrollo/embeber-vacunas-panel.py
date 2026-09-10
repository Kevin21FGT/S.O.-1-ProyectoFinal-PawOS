#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Agenda de Vacunas" de ventana emergente a panel embebido en
el contenido principal, igual que ya se hizo con "Gestion de Mascotas".

No se toca ninguna logica de negocio: cargar_vacunas(), on_ver_todas_
vacunas_clicked, on_ver_pendientes_vacunas_clicked y on_registrar_
vacuna_clicked quedan exactamente iguales (siguen recibiendo el mismo
ContextoVacunas* de siempre). Solo cambia donde vive el contenido:
- abrir_pantalla_vacunas ya no crea su propia ventana (gtk_window_new);
  arma la misma caja de contenido y la muestra dentro del area_dinamica
  del menu principal.
- ctx->ventana pasa a apuntar a la ventana principal (se sigue usando
  igual como padre de los sub-dialogos de registrar vacuna).
- El boton "Cerrar" ahora vuelve a la pantalla de bienvenida del panel
  en vez de destruir una ventana.
- on_vacunas_clicked pasa tambien el area_dinamica, igual que ya se hizo
  con on_mascotas_clicked.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_vacunas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_vacunas(d->ventana_principal, d->rol);
}'''

NUEVO_CLICKED = r'''static void on_vacunas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_vacunas(d->area_dinamica, d->ventana_principal, d->rol);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_vacunas(GtkWidget *padre, Rol rol) {
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
    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void abrir_pantalla_vacunas(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    ContextoVacunas *ctx = g_malloc0(sizeof(ContextoVacunas));
    ctx->rol = rol;
    ctx->solo_pendientes = FALSE;
    ctx->ventana = ventana_principal;

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-vacunas", ctx, g_free);

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
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    cargar_vacunas(ctx);
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
    print("Cambios aplicados:")
    print("  - Agenda de Vacunas ahora se abre embebida en el panel principal")
    print("  - Sub-dialogos (ver todas/pendientes/registrar) siguen funcionando igual")


if __name__ == "__main__":
    main()
