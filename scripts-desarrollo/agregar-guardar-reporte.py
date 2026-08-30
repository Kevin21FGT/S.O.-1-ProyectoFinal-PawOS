#!/usr/bin/env python3
# agregar-guardar-reporte.py - Agrega un boton "Guardar como..." a la
# pantalla de Reportes: abre el dialogo normal de "Guardar archivo" de
# GTK (eligiendo carpeta y nombre), con opcion de .txt o .pdf. No toca
# el boton "Generar reporte" que ya existe y sigue funcionando igual.
import shutil

RUTA = "src/main_gtk.c"

with open(RUTA) as f:
    contenido = f.read()

if "on_guardar_como_reporte_clicked" in contenido:
    print("Ya estaba aplicado, no se toca nada.")
    raise SystemExit(0)

shutil.copy(RUTA, RUTA + ".bak")

cambios = 0

# 1) include de cairo-pdf (ya viene con libgtk-3-dev, no hace falta
#    instalar nada nuevo)
viejo = "#include <gtk/gtk.h>\n"
nuevo = "#include <gtk/gtk.h>\n#include <cairo-pdf.h>\n"
if viejo not in contenido:
    print("NO SE ENCONTRO el include de gtk.h -- abortando")
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

# 2) agregar el campo btn_guardar al contexto de Reportes
viejo = '''typedef struct {
    GtkWidget *ventana;
    GtkWidget *vista_texto;
    GtkWidget *lbl_estado;
} ContextoReportes;'''
nuevo = '''typedef struct {
    GtkWidget *ventana;
    GtkWidget *vista_texto;
    GtkWidget *lbl_estado;
    GtkWidget *btn_guardar;
} ContextoReportes;'''
if viejo not in contenido:
    print("NO SE ENCONTRO ContextoReportes -- abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

# 3) agregar escribir_pdf_simple() justo antes de on_generar_reporte_clicked
viejo = "static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {"
nuevo = '''/* Escribe el contenido de texto plano de un reporte a un PDF simple:
 * fuente monoespaciada, una linea de texto por linea del reporte, con
 * paginacion automatica al llenarse la hoja (tamano carta). No hace
 * falta ninguna libreria nueva: usa Cairo, que ya viene con GTK3. */
static gboolean escribir_pdf_simple(const char *ruta, const char *contenido) {
    const double ancho = 612.0, alto = 792.0; /* carta (Letter), en puntos */
    const double margen = 40.0;
    const double tam_fuente = 10.0;
    const double interlineado = 14.0;

    cairo_surface_t *superficie = cairo_pdf_surface_create(ruta, ancho, alto);
    if (cairo_surface_status(superficie) != CAIRO_STATUS_SUCCESS) {
        cairo_surface_destroy(superficie);
        return FALSE;
    }
    cairo_t *cr = cairo_create(superficie);
    cairo_select_font_face(cr, "Monospace", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr, tam_fuente);
    cairo_set_source_rgb(cr, 0, 0, 0);

    double y = margen + tam_fuente;
    gchar **lineas = g_strsplit(contenido, "\\n", -1);
    for (int i = 0; lineas[i] != NULL; i++) {
        if (y > alto - margen) {
            cairo_show_page(cr);
            cairo_set_source_rgb(cr, 0, 0, 0);
            y = margen + tam_fuente;
        }
        cairo_move_to(cr, margen, y);
        cairo_show_text(cr, lineas[i]);
        y += interlineado;
    }
    g_strfreev(lineas);

    cairo_show_page(cr);
    cairo_status_t estado = cairo_status(cr);
    cairo_destroy(cr);
    cairo_surface_destroy(superficie);
    return estado == CAIRO_STATUS_SUCCESS;
}

static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {'''
if viejo not in contenido:
    print("NO SE ENCONTRO on_generar_reporte_clicked -- abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

# 4) al terminar de generar bien el reporte, habilitar el boton "Guardar como..."
viejo = '''    char estado_txt[200];
    snprintf(estado_txt, sizeof(estado_txt), "Reporte generado en: %s", ruta_usada);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), estado_txt);
    mostrar_contenido_archivo(GTK_TEXT_VIEW(ctx->vista_texto), ruta_usada);
}'''
nuevo = '''    char estado_txt[200];
    snprintf(estado_txt, sizeof(estado_txt), "Reporte generado en: %s", ruta_usada);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), estado_txt);
    mostrar_contenido_archivo(GTK_TEXT_VIEW(ctx->vista_texto), ruta_usada);
    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);
}

/* Abre el dialogo estandar de "Guardar archivo" de GTK (el usuario
 * elige carpeta y nombre libremente, no queda forzado a la ruta fija
 * del sistema) y guarda el reporte ya generado como .txt o .pdf, segun
 * el filtro que elija o la extension que escriba. */
static void on_guardar_como_reporte_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoReportes *ctx = (ContextoReportes *)datos;

    GtkWidget *dialogo = gtk_file_chooser_dialog_new(
        "Guardar reporte como...", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_SAVE,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_ACCEPT, NULL);
    gtk_file_chooser_set_do_overwrite_confirmation(GTK_FILE_CHOOSER(dialogo), TRUE);
    gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(dialogo), "reporte_pawos.txt");

    const char *carpeta_inicial = g_get_home_dir();
    if (carpeta_inicial != NULL) {
        gtk_file_chooser_set_current_folder(GTK_FILE_CHOOSER(dialogo), carpeta_inicial);
    }

    GtkFileFilter *filtro_txt = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro_txt, "Texto (*.txt)");
    gtk_file_filter_add_pattern(filtro_txt, "*.txt");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro_txt);

    GtkFileFilter *filtro_pdf = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro_pdf, "PDF (*.pdf)");
    gtk_file_filter_add_pattern(filtro_pdf, "*.pdf");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro_pdf);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(dialogo);
        return;
    }

    gchar *ruta_elegida = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialogo));
    GtkFileFilter *filtro_activo = gtk_file_chooser_get_filter(GTK_FILE_CHOOSER(dialogo));
    gtk_widget_destroy(dialogo);
    if (ruta_elegida == NULL) return;

    gboolean quiere_pdf = (filtro_activo == filtro_pdf) || g_str_has_suffix(ruta_elegida, ".pdf");

    gchar *ruta_final = ruta_elegida;
    if (!g_str_has_suffix(ruta_elegida, ".pdf") && !g_str_has_suffix(ruta_elegida, ".txt")) {
        ruta_final = g_strconcat(ruta_elegida, quiere_pdf ? ".pdf" : ".txt", NULL);
        g_free(ruta_elegida);
    }

    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(ctx->vista_texto));
    GtkTextIter inicio, fin;
    gtk_text_buffer_get_bounds(buffer, &inicio, &fin);
    gchar *contenido_reporte = gtk_text_buffer_get_text(buffer, &inicio, &fin, FALSE);

    gboolean ok;
    if (quiere_pdf) {
        ok = escribir_pdf_simple(ruta_final, contenido_reporte);
    } else {
        GError *error = NULL;
        ok = g_file_set_contents(ruta_final, contenido_reporte, -1, &error);
        if (error) g_error_free(error);
    }

    if (ok) {
        char msg[600];
        snprintf(msg, sizeof(msg), "Reporte guardado en:\\n%s", ruta_final);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
    } else {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar el reporte en esa ubicacion.", TRUE);
    }

    g_free(contenido_reporte);
    g_free(ruta_final);
}'''
if viejo not in contenido:
    print("NO SE ENCONTRO el final de on_generar_reporte_clicked -- abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

# 5) agregar el boton en la pantalla, deshabilitado hasta que se genere
#    un reporte
viejo = '''    GtkWidget *btn_generar = gtk_button_new_with_label("Generar reporte");
    gtk_widget_set_halign(btn_generar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_generar, FALSE, FALSE, 0);'''
nuevo = '''    GtkWidget *btn_generar = gtk_button_new_with_label("Generar reporte");
    gtk_widget_set_halign(btn_generar, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), btn_generar, FALSE, FALSE, 0);

    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);'''
if viejo not in contenido:
    print("NO SE ENCONTRO el bloque de btn_generar -- abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

# 6) conectar la señal del boton nuevo
viejo = '''    g_signal_connect(btn_generar, "clicked", G_CALLBACK(on_generar_reporte_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Administracion de Procesos (solo Administrador)'''
nuevo = '''    g_signal_connect(btn_generar, "clicked", G_CALLBACK(on_generar_reporte_clicked), ctx);
    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    gtk_widget_show_all(ctx->ventana);
}

/* =================================================================
 * Modulo: Administracion de Procesos (solo Administrador)'''
if viejo not in contenido:
    print("NO SE ENCONTRO el bloque de señales finales de Reportes -- abortando")
    shutil.copy(RUTA + ".bak", RUTA)
    raise SystemExit(1)
contenido = contenido.replace(viejo, nuevo, 1)
cambios += 1

with open(RUTA, "w") as f:
    f.write(contenido)

print(f"Listo: {cambios} bloques aplicados.")
