#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Administracion de Memoria" de ventana emergente a panel
embebido. No toca actualizar_estadisticas_memoria(), ni ninguno de los
manejadores on_refrescar_memoria_clicked, on_crear_proceso_demo_clicked,
on_asignar_memoria_clicked, on_probar_lectura_escritura_clicked,
on_destruir_proceso_demo_clicked, ni la restriccion de "solo Admin".
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_memoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso denegado: esta seccion es solo para el Administrador.", TRUE);
        return;
    }
    abrir_pantalla_memoria(d->ventana_principal);
}'''

NUEVO_CLICKED = r'''static void on_memoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol != ROL_ADMIN) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso denegado: esta seccion es solo para el Administrador.", TRUE);
        return;
    }
    abrir_pantalla_memoria(d->area_dinamica, d->ventana_principal);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_memoria(GtkWidget *padre) {
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
    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void abrir_pantalla_memoria(GtkWidget *area_dinamica, GtkWidget *ventana_principal) {
    ContextoMemoria *ctx = g_malloc0(sizeof(ContextoMemoria));
    ctx->ventana = ventana_principal;

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-memoria", ctx, g_free);

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
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    actualizar_estadisticas_memoria(ctx);
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
    print("Administracion de Memoria ahora se abre embebida en el panel principal")


if __name__ == "__main__":
    main()
