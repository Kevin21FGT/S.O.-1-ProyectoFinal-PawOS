#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Respaldo en la Nube" de ventana emergente a panel embebido.

Este modulo tiene un detalle que los anteriores no tenian: su limpieza
(liberar_contexto_respaldo) no solo libera memoria, tambien marca
*ctx->vivo = FALSE antes de liberar. Ese flag "vivo" existe para que
operaciones en curso (como una tarea de respaldo o restauracion que
sigue corriendo en segundo plano) puedan revisar si el contexto
todavia existe antes de tocarlo. Para no perder esa logica, se agrega
una funcion nueva (liberar_contexto_respaldo_gdestroy) con la firma
correcta que exige g_object_set_data_full (GDestroyNotify, un solo
parametro), pero que hace EXACTAMENTE lo mismo que la funcion original.
La funcion original liberar_contexto_respaldo se deja intacta -- sigue
existiendo por si algo mas la usa, no se toca ni se borra.

No se toca ninguna otra logica: actualizar_estado_respaldo,
actualizar_ui_modo_respaldo, cargar_historial_respaldos, ni ninguno de
los manejadores de los botones (actualizar, respaldar ahora, guardar
config, restaurar, radio modo).
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_respaldo(d->ventana_principal, d->rol);
}'''

NUEVO_CLICKED = r'''static void on_respaldo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_respaldo(d->area_dinamica, d->ventana_principal, d->rol);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_respaldo(GtkWidget *padre, Rol rol) {
    ContextoRespaldo *ctx = g_malloc0(sizeof(ContextoRespaldo));
    ctx->rol = rol;
    ctx->vivo = g_new(gboolean, 1);
    *ctx->vivo = TRUE;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Respaldo en la Nube");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 580, 700);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 16);

    /* caja_raiz separa el contenido (que puede crecer, por eso va
     * dentro de un GtkScrolledWindow) de la fila de botones de abajo
     * (Actualizar/Respaldar/Cerrar), que se queda siempre fija y
     * visible sin importar cuanto contenido haya arriba o que tan
     * chica quede la ventana. Antes todo iba en una sola caja sin
     * scroll, y al agregar la etiqueta por defecto el contenido crecio
     * lo suficiente para que los botones de abajo quedaran fuera del
     * area visible en ventanas mas chicas. */
    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    GtkWidget *scroll_principal = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_principal),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_principal, TRUE, TRUE, 0);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(scroll_principal), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Respaldo en la Nube</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "La base de datos del refugio se respalda automaticamente hacia Google Drive\n"
        "todas las noches (rclone + temporizador de systemd). Aqui puedes ver el\n"
        "estado de ese respaldo o dispararlo manualmente antes de tiempo.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *marco = gtk_frame_new("Estado actual");
    GtkWidget *caja_marco = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_marco), 10);
    gtk_container_add(GTK_CONTAINER(marco), caja_marco);

    ctx->lbl_ultimo = gtk_label_new("Ultimo respaldo automatico: -");
    ctx->lbl_estado = gtk_label_new("Estado del servicio: -");
    gtk_widget_set_halign(ctx->lbl_ultimo, GTK_ALIGN_START);
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_label_set_line_wrap(GTK_LABEL(ctx->lbl_ultimo), TRUE);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_ultimo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), marco, FALSE, FALSE, 0);

    /* --- Configuracion: Automatico (con intervalo) o Manual --- */
    GtkWidget *marco_config = gtk_frame_new("Configuracion del respaldo");
    GtkWidget *caja_config = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_config), 10);
    gtk_container_add(GTK_CONTAINER(marco_config), caja_config);

    ctx->lbl_modo = gtk_label_new("Modo actual: -");
    gtk_widget_set_halign(ctx->lbl_modo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->lbl_modo, FALSE, FALSE, 0);

    ctx->radio_auto = gtk_radio_button_new_with_label(NULL, "Automatico");
    ctx->radio_manual = gtk_radio_button_new_with_label_from_widget(
        GTK_RADIO_BUTTON(ctx->radio_auto), "Manual (solo con 'Respaldar ahora')");
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_auto, FALSE, FALSE, 0);

    ctx->combo_intervalo = gtk_combo_box_text_new();
    for (int i = 0; i < N_INTERVALOS; i++) {
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(ctx->combo_intervalo), INTERVALOS_ETIQUETA[i]);
    }
    gtk_combo_box_set_active(GTK_COMBO_BOX(ctx->combo_intervalo), 0);
    gtk_widget_set_margin_start(ctx->combo_intervalo, 24);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->combo_intervalo, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_manual, FALSE, FALSE, 0);

    GtkWidget *lbl_etiqueta_auto = gtk_label_new(
        "Etiqueta por defecto (opcional, se usa si 'Respaldar ahora' se deja\n"
        "en blanco, y tambien en el respaldo automatico):");
    gtk_widget_set_halign(lbl_etiqueta_auto, GTK_ALIGN_START);
    gtk_widget_set_margin_top(lbl_etiqueta_auto, 6);
    gtk_box_pack_start(GTK_BOX(caja_config), lbl_etiqueta_auto, FALSE, FALSE, 0);

    ctx->entrada_etiqueta_auto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ctx->entrada_etiqueta_auto),
        "ej. refugio-principal (deja vacio para no usar ninguna)");
    gtk_entry_set_max_length(GTK_ENTRY(ctx->entrada_etiqueta_auto), 40);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->entrada_etiqueta_auto, FALSE, FALSE, 0);

    GtkWidget *btn_guardar_config = gtk_button_new_with_label("Guardar configuracion");
    gtk_widget_set_halign(btn_guardar_config, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), btn_guardar_config, FALSE, FALSE, 4);

    gtk_box_pack_start(GTK_BOX(caja), marco_config, FALSE, FALSE, 0);

    /* --- Historial de respaldos: registro de lo que ya hay guardado en
     * Google Drive, por si hay que recuperar la base de datos despues
     * de un borrado accidental. --- */
    GtkWidget *marco_historial = gtk_frame_new("Historial de respaldos (Google Drive)");
    GtkWidget *caja_historial = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_historial), 10);
    gtk_container_add(GTK_CONTAINER(marco_historial), caja_historial);

    GtkWidget *lbl_historial = gtk_label_new(
        "Cada respaldo queda guardado por separado (no se pisan entre si).\n"
        "Al usar 'Respaldar ahora' puedes ponerle una etiqueta para reconocerlo\n"
        "despues. Selecciona uno y usa 'Restaurar seleccionado' para recuperarlo.");
    gtk_label_set_justify(GTK_LABEL(lbl_historial), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), lbl_historial, FALSE, FALSE, 0);

    ctx->modelo_historial = gtk_list_store_new(N_COL_HIST,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->lista_historial = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->modelo_historial));

    GtkCellRenderer *render_fecha = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Fecha del respaldo", render_fecha, "text", COL_HIST_FECHA, NULL);
    GtkCellRenderer *render_etiqueta = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Etiqueta", render_etiqueta, "text", COL_HIST_ETIQUETA, NULL);
    GtkCellRenderer *render_tamano = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Tamano (bytes)", render_tamano, "text", COL_HIST_TAMANO, NULL);

    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 140);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->lista_historial);
    gtk_box_pack_start(GTK_BOX(caja_historial), scroll_historial, TRUE, TRUE, 0);

    ctx->btn_restaurar = gtk_button_new_with_label("Restaurar seleccionado");
    gtk_widget_set_halign(ctx->btn_restaurar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), ctx->btn_restaurar, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja), marco_historial, TRUE, TRUE, 0);

    /* Fuera del scroll a proposito (ver comentario en caja_raiz, arriba):
     * estos botones siempre tienen que estar visibles. */
    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja_raiz), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar estado");
    GtkWidget *btn_respaldar  = gtk_button_new_with_label("Respaldar ahora");
    GtkWidget *btn_cerrar     = gtk_button_new_with_label("Cerrar");
    ctx->btn_actualizar = btn_actualizar;

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_respaldar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que Procesos/Memoria: se muestra siempre, solo se
     * deshabilita para quien no sea Administrador. */
    if (rol != ROL_ADMIN) {
        gtk_widget_set_sensitive(btn_respaldar, FALSE);
        gtk_widget_set_tooltip_text(btn_respaldar, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->radio_auto, FALSE);
        gtk_widget_set_sensitive(ctx->radio_manual, FALSE);
        gtk_widget_set_sensitive(ctx->combo_intervalo, FALSE);
        gtk_widget_set_sensitive(ctx->entrada_etiqueta_auto, FALSE);
        gtk_widget_set_sensitive(btn_guardar_config, FALSE);
        gtk_widget_set_tooltip_text(btn_guardar_config, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->btn_restaurar, FALSE);
        gtk_widget_set_tooltip_text(ctx->btn_restaurar, "Requiere rol Administrador.");
    }

    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_estado_respaldo_clicked), ctx);
    g_signal_connect(btn_respaldar, "clicked", G_CALLBACK(on_respaldar_ahora_clicked), ctx);
    g_signal_connect(ctx->radio_auto, "toggled", G_CALLBACK(on_radio_modo_respaldo_toggled), ctx);
    g_signal_connect(btn_guardar_config, "clicked", G_CALLBACK(on_guardar_config_respaldo_clicked), ctx);
    g_signal_connect(ctx->btn_restaurar, "clicked", G_CALLBACK(on_restaurar_respaldo_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto_respaldo), ctx);

    actualizar_estado_respaldo(ctx);
    actualizar_ui_modo_respaldo(ctx);
    cargar_historial_respaldos(ctx);
    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void liberar_contexto_respaldo_gdestroy(gpointer datos) {
    ContextoRespaldo *ctx = (ContextoRespaldo *)datos;
    if (ctx->vivo) *ctx->vivo = FALSE;
    g_free(ctx);
}

static void abrir_pantalla_respaldo(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    ContextoRespaldo *ctx = g_malloc0(sizeof(ContextoRespaldo));
    ctx->rol = rol;
    ctx->vivo = g_new(gboolean, 1);
    *ctx->vivo = TRUE;
    ctx->ventana = ventana_principal;

    /* caja_raiz separa el contenido (que puede crecer, por eso va
     * dentro de un GtkScrolledWindow) de la fila de botones de abajo
     * (Actualizar/Respaldar/Cerrar), que se queda siempre fija y
     * visible sin importar cuanto contenido haya arriba o que tan
     * chica quede la ventana. Antes todo iba en una sola caja sin
     * scroll, y al agregar la etiqueta por defecto el contenido crecio
     * lo suficiente para que los botones de abajo quedaran fuera del
     * area visible en ventanas mas chicas. */
    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    g_object_set_data_full(G_OBJECT(caja_raiz), "pawos-contexto-respaldo", ctx, liberar_contexto_respaldo_gdestroy);

    GtkWidget *scroll_principal = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_principal),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_principal, TRUE, TRUE, 0);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(scroll_principal), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Respaldo en la Nube</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "La base de datos del refugio se respalda automaticamente hacia Google Drive\n"
        "todas las noches (rclone + temporizador de systemd). Aqui puedes ver el\n"
        "estado de ese respaldo o dispararlo manualmente antes de tiempo.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *marco = gtk_frame_new("Estado actual");
    GtkWidget *caja_marco = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_marco), 10);
    gtk_container_add(GTK_CONTAINER(marco), caja_marco);

    ctx->lbl_ultimo = gtk_label_new("Ultimo respaldo automatico: -");
    ctx->lbl_estado = gtk_label_new("Estado del servicio: -");
    gtk_widget_set_halign(ctx->lbl_ultimo, GTK_ALIGN_START);
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_label_set_line_wrap(GTK_LABEL(ctx->lbl_ultimo), TRUE);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_ultimo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_marco), ctx->lbl_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja), marco, FALSE, FALSE, 0);

    /* --- Configuracion: Automatico (con intervalo) o Manual --- */
    GtkWidget *marco_config = gtk_frame_new("Configuracion del respaldo");
    GtkWidget *caja_config = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_config), 10);
    gtk_container_add(GTK_CONTAINER(marco_config), caja_config);

    ctx->lbl_modo = gtk_label_new("Modo actual: -");
    gtk_widget_set_halign(ctx->lbl_modo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->lbl_modo, FALSE, FALSE, 0);

    ctx->radio_auto = gtk_radio_button_new_with_label(NULL, "Automatico");
    ctx->radio_manual = gtk_radio_button_new_with_label_from_widget(
        GTK_RADIO_BUTTON(ctx->radio_auto), "Manual (solo con 'Respaldar ahora')");
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_auto, FALSE, FALSE, 0);

    ctx->combo_intervalo = gtk_combo_box_text_new();
    for (int i = 0; i < N_INTERVALOS; i++) {
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(ctx->combo_intervalo), INTERVALOS_ETIQUETA[i]);
    }
    gtk_combo_box_set_active(GTK_COMBO_BOX(ctx->combo_intervalo), 0);
    gtk_widget_set_margin_start(ctx->combo_intervalo, 24);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->combo_intervalo, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja_config), ctx->radio_manual, FALSE, FALSE, 0);

    GtkWidget *lbl_etiqueta_auto = gtk_label_new(
        "Etiqueta por defecto (opcional, se usa si 'Respaldar ahora' se deja\n"
        "en blanco, y tambien en el respaldo automatico):");
    gtk_widget_set_halign(lbl_etiqueta_auto, GTK_ALIGN_START);
    gtk_widget_set_margin_top(lbl_etiqueta_auto, 6);
    gtk_box_pack_start(GTK_BOX(caja_config), lbl_etiqueta_auto, FALSE, FALSE, 0);

    ctx->entrada_etiqueta_auto = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(ctx->entrada_etiqueta_auto),
        "ej. refugio-principal (deja vacio para no usar ninguna)");
    gtk_entry_set_max_length(GTK_ENTRY(ctx->entrada_etiqueta_auto), 40);
    gtk_box_pack_start(GTK_BOX(caja_config), ctx->entrada_etiqueta_auto, FALSE, FALSE, 0);

    GtkWidget *btn_guardar_config = gtk_button_new_with_label("Guardar configuracion");
    gtk_widget_set_halign(btn_guardar_config, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_config), btn_guardar_config, FALSE, FALSE, 4);

    gtk_box_pack_start(GTK_BOX(caja), marco_config, FALSE, FALSE, 0);

    /* --- Historial de respaldos: registro de lo que ya hay guardado en
     * Google Drive, por si hay que recuperar la base de datos despues
     * de un borrado accidental. --- */
    GtkWidget *marco_historial = gtk_frame_new("Historial de respaldos (Google Drive)");
    GtkWidget *caja_historial = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_set_border_width(GTK_CONTAINER(caja_historial), 10);
    gtk_container_add(GTK_CONTAINER(marco_historial), caja_historial);

    GtkWidget *lbl_historial = gtk_label_new(
        "Cada respaldo queda guardado por separado (no se pisan entre si).\n"
        "Al usar 'Respaldar ahora' puedes ponerle una etiqueta para reconocerlo\n"
        "despues. Selecciona uno y usa 'Restaurar seleccionado' para recuperarlo.");
    gtk_label_set_justify(GTK_LABEL(lbl_historial), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), lbl_historial, FALSE, FALSE, 0);

    ctx->modelo_historial = gtk_list_store_new(N_COL_HIST,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->lista_historial = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->modelo_historial));

    GtkCellRenderer *render_fecha = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Fecha del respaldo", render_fecha, "text", COL_HIST_FECHA, NULL);
    GtkCellRenderer *render_etiqueta = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Etiqueta", render_etiqueta, "text", COL_HIST_ETIQUETA, NULL);
    GtkCellRenderer *render_tamano = gtk_cell_renderer_text_new();
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(ctx->lista_historial), -1,
        "Tamano (bytes)", render_tamano, "text", COL_HIST_TAMANO, NULL);

    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial),
        GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 140);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->lista_historial);
    gtk_box_pack_start(GTK_BOX(caja_historial), scroll_historial, TRUE, TRUE, 0);

    ctx->btn_restaurar = gtk_button_new_with_label("Restaurar seleccionado");
    gtk_widget_set_halign(ctx->btn_restaurar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_historial), ctx->btn_restaurar, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(caja), marco_historial, TRUE, TRUE, 0);

    /* Fuera del scroll a proposito (ver comentario en caja_raiz, arriba):
     * estos botones siempre tienen que estar visibles. */
    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja_raiz), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar estado");
    GtkWidget *btn_respaldar  = gtk_button_new_with_label("Respaldar ahora");
    GtkWidget *btn_cerrar     = gtk_button_new_with_label("Cerrar");
    ctx->btn_actualizar = btn_actualizar;

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_respaldar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que Procesos/Memoria: se muestra siempre, solo se
     * deshabilita para quien no sea Administrador. */
    if (rol != ROL_ADMIN) {
        gtk_widget_set_sensitive(btn_respaldar, FALSE);
        gtk_widget_set_tooltip_text(btn_respaldar, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->radio_auto, FALSE);
        gtk_widget_set_sensitive(ctx->radio_manual, FALSE);
        gtk_widget_set_sensitive(ctx->combo_intervalo, FALSE);
        gtk_widget_set_sensitive(ctx->entrada_etiqueta_auto, FALSE);
        gtk_widget_set_sensitive(btn_guardar_config, FALSE);
        gtk_widget_set_tooltip_text(btn_guardar_config, "Requiere rol Administrador.");
        gtk_widget_set_sensitive(ctx->btn_restaurar, FALSE);
        gtk_widget_set_tooltip_text(ctx->btn_restaurar, "Requiere rol Administrador.");
    }

    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_estado_respaldo_clicked), ctx);
    g_signal_connect(btn_respaldar, "clicked", G_CALLBACK(on_respaldar_ahora_clicked), ctx);
    g_signal_connect(ctx->radio_auto, "toggled", G_CALLBACK(on_radio_modo_respaldo_toggled), ctx);
    g_signal_connect(btn_guardar_config, "clicked", G_CALLBACK(on_guardar_config_respaldo_clicked), ctx);
    g_signal_connect(ctx->btn_restaurar, "clicked", G_CALLBACK(on_restaurar_respaldo_clicked), ctx);
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    actualizar_estado_respaldo(ctx);
    actualizar_ui_modo_respaldo(ctx);
    cargar_historial_respaldos(ctx);
    mostrar_en_panel(area_dinamica, caja_raiz);
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
    print("Respaldo en la Nube ahora se abre embebido en el panel principal")
    print("(se agrego liberar_contexto_respaldo_gdestroy, con la misma logica del flag 'vivo')")


if __name__ == "__main__":
    main()
