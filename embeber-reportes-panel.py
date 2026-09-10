#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte "Reportes" de ventana emergente a panel embebido. No toca
cargar_historial(), on_generar_reporte_clicked, on_guardar_como_reporte_
clicked, on_generar_reporte_categoria_clicked, ni los generadores
reporte_generar_* -- toda esa logica queda exactamente igual.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_CLICKED = r'''static void on_reportes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol == ROL_VOLUNTARIO) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso restringido: este modulo requiere rol Admin o Veterinario.", TRUE);
        return;
    }
    abrir_pantalla_reportes(d->ventana_principal, d->rol);
}'''

NUEVO_CLICKED = r'''static void on_reportes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    if (d->rol == ROL_VOLUNTARIO) {
        mostrar_mensaje(GTK_WINDOW(d->ventana_principal),
            "Acceso restringido: este modulo requiere rol Admin o Veterinario.", TRUE);
        return;
    }
    abrir_pantalla_reportes(d->area_dinamica, d->ventana_principal, d->rol);
}'''

ANCLA_ABRIR = r'''static void abrir_pantalla_reportes(GtkWidget *padre, Rol rol) {
    (void)rol; /* ya se filtro el acceso antes de llamar a esta funcion */

    ContextoReportes *ctx = g_malloc0(sizeof(ContextoReportes));

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Reportes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 640, 480);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Reportes</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "Genera un resumen del estado del refugio (mascotas, vacunas, adopciones y donantes)\n"
        "en un archivo de texto dentro del sistema.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *btn_generar = gtk_button_new_with_label("Generar reporte");
    gtk_widget_set_halign(btn_generar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_generar, FALSE, FALSE, 0);

    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);

    GtkWidget *lbl_categorias = gtk_label_new("Reportes por categoria:");
    gtk_widget_set_halign(lbl_categorias, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_categorias, FALSE, FALSE, 4);

    GtkWidget *caja_categorias = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(caja), caja_categorias, FALSE, FALSE, 0);

    static const char *nombres_categorias[5] = {
        "Mascotas", "Vacunas", "Adopciones", "Donantes", "Alertas de Sensores"
    };
    static const char *rutas_fijas_categorias[5] = {
        "/var/pawos/reportes/reporte_mascotas.txt",
        "/var/pawos/reportes/reporte_vacunas.txt",
        "/var/pawos/reportes/reporte_adopciones.txt",
        "/var/pawos/reportes/reporte_donantes.txt",
        "/var/pawos/reportes/reporte_alertas.txt"
    };
    static const char *rutas_relativas_categorias[5] = {
        "reporte_mascotas.txt", "reporte_vacunas.txt", "reporte_adopciones.txt",
        "reporte_donantes.txt", "reporte_alertas.txt"
    };
    int (*generadores_categorias[5])(const char *) = {
        reporte_generar_mascotas, reporte_generar_vacunas, reporte_generar_adopciones,
        reporte_generar_donantes, reporte_generar_alertas
    };
    for (int i = 0; i < 5; i++) {
        GtkWidget *btn_cat = gtk_button_new_with_label(nombres_categorias[i]);
        gtk_box_pack_start(GTK_BOX(caja_categorias), btn_cat, FALSE, FALSE, 0);
        DatosReporteCategoria *d = g_new0(DatosReporteCategoria, 1);
        d->ctx = ctx;
        d->nombre_tipo = nombres_categorias[i];
        d->generador = generadores_categorias[i];
        d->ruta_fija = rutas_fijas_categorias[i];
        d->ruta_relativa = rutas_relativas_categorias[i];
        g_signal_connect(btn_cat, "clicked", G_CALLBACK(on_generar_reporte_categoria_clicked), d);
    }

    ctx->lbl_estado = gtk_label_new("Todavia no se ha generado ningun reporte en esta sesion.");
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), ctx->lbl_estado, FALSE, FALSE, 0);

    ctx->vista_texto = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_texto), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_texto), TRUE);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->vista_texto);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *lbl_historial = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_historial), "<b>Historial de reportes generados</b>");
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_historial, FALSE, FALSE, 4);

    ctx->vista_historial = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_historial), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_historial), TRUE);
    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 110);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->vista_historial);
    gtk_box_pack_start(GTK_BOX(caja), scroll_historial, FALSE, FALSE, 0);
    cargar_historial(ctx);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    gtk_widget_set_halign(btn_cerrar, GTK_ALIGN_END);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_generar, "clicked", G_CALLBACK(on_generar_reporte_clicked), ctx);
    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void abrir_pantalla_reportes(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    (void)rol; /* ya se filtro el acceso antes de llamar a esta funcion */

    ContextoReportes *ctx = g_malloc0(sizeof(ContextoReportes));
    ctx->ventana = ventana_principal;

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-reportes", ctx, g_free);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Reportes</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *descripcion = gtk_label_new(
        "Genera un resumen del estado del refugio (mascotas, vacunas, adopciones y donantes)\n"
        "en un archivo de texto dentro del sistema.");
    gtk_label_set_justify(GTK_LABEL(descripcion), GTK_JUSTIFY_LEFT);
    gtk_widget_set_halign(descripcion, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), descripcion, FALSE, FALSE, 0);

    GtkWidget *btn_generar = gtk_button_new_with_label("Generar reporte");
    gtk_widget_set_halign(btn_generar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_generar, FALSE, FALSE, 0);

    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);

    GtkWidget *lbl_categorias = gtk_label_new("Reportes por categoria:");
    gtk_widget_set_halign(lbl_categorias, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_categorias, FALSE, FALSE, 4);

    GtkWidget *caja_categorias = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(caja), caja_categorias, FALSE, FALSE, 0);

    static const char *nombres_categorias[5] = {
        "Mascotas", "Vacunas", "Adopciones", "Donantes", "Alertas de Sensores"
    };
    static const char *rutas_fijas_categorias[5] = {
        "/var/pawos/reportes/reporte_mascotas.txt",
        "/var/pawos/reportes/reporte_vacunas.txt",
        "/var/pawos/reportes/reporte_adopciones.txt",
        "/var/pawos/reportes/reporte_donantes.txt",
        "/var/pawos/reportes/reporte_alertas.txt"
    };
    static const char *rutas_relativas_categorias[5] = {
        "reporte_mascotas.txt", "reporte_vacunas.txt", "reporte_adopciones.txt",
        "reporte_donantes.txt", "reporte_alertas.txt"
    };
    int (*generadores_categorias[5])(const char *) = {
        reporte_generar_mascotas, reporte_generar_vacunas, reporte_generar_adopciones,
        reporte_generar_donantes, reporte_generar_alertas
    };
    for (int i = 0; i < 5; i++) {
        GtkWidget *btn_cat = gtk_button_new_with_label(nombres_categorias[i]);
        gtk_box_pack_start(GTK_BOX(caja_categorias), btn_cat, FALSE, FALSE, 0);
        DatosReporteCategoria *d = g_new0(DatosReporteCategoria, 1);
        d->ctx = ctx;
        d->nombre_tipo = nombres_categorias[i];
        d->generador = generadores_categorias[i];
        d->ruta_fija = rutas_fijas_categorias[i];
        d->ruta_relativa = rutas_relativas_categorias[i];
        g_signal_connect(btn_cat, "clicked", G_CALLBACK(on_generar_reporte_categoria_clicked), d);
    }

    ctx->lbl_estado = gtk_label_new("Todavia no se ha generado ningun reporte en esta sesion.");
    gtk_widget_set_halign(ctx->lbl_estado, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), ctx->lbl_estado, FALSE, FALSE, 0);

    ctx->vista_texto = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_texto), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_texto), TRUE);
    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->vista_texto);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *lbl_historial = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_historial), "<b>Historial de reportes generados</b>");
    gtk_widget_set_halign(lbl_historial, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_historial, FALSE, FALSE, 4);

    ctx->vista_historial = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(ctx->vista_historial), FALSE);
    gtk_text_view_set_monospace(GTK_TEXT_VIEW(ctx->vista_historial), TRUE);
    GtkWidget *scroll_historial = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_historial), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroll_historial, -1, 110);
    gtk_container_add(GTK_CONTAINER(scroll_historial), ctx->vista_historial);
    gtk_box_pack_start(GTK_BOX(caja), scroll_historial, FALSE, FALSE, 0);
    cargar_historial(ctx);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    gtk_widget_set_halign(btn_cerrar, GTK_ALIGN_END);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    g_signal_connect(btn_generar, "clicked", G_CALLBACK(on_generar_reporte_clicked), ctx);
    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);
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
    print("Reportes ahora se abre embebido en el panel principal")


if __name__ == "__main__":
    main()
