#!/usr/bin/env python3
"""
parche-reportes-enviar.py   (despues de parche-reportes-pdf.py)

Reportes: junto a "Guardar como" aparecen dos botones nuevos,
"Enviar por correo" y "Enviar por WhatsApp". Funcionan para el reporte que
este en pantalla (las 5 categorias: Mascotas, Vacunas, Adopciones, Donantes y
Alertas, con el mes elegido, y tambien el reporte general):

  1. Pide el correo o el numero de destino (a un numero de 8 digitos le agrega
     502, igual que el recordatorio de vacunas).
  2. Genera el PDF con diseno en una carpeta temporal.
  3. Lo manda con pawos-enviar-documento (mismas credenciales y misma regla de
     sudo que ya usa el Portal; si falta, avisa que correr instalar-documentos.sh).
  4. Borra el PDF temporal.

Los botones se activan cuando ya hay un reporte generado.

Uso (parado en la raiz del repo):
    python3 parche-reportes-enviar.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

GTK_C = "src/main_gtk.c"
MARCA = "on_enviar_reporte_correo_clicked"

# 1) campos nuevos en el contexto
A1 = """    GtkWidget *btn_guardar;
} ContextoReportes;"""
N1 = """    GtkWidget *btn_guardar;
    GtkWidget *btn_correo;
    GtkWidget *btn_whatsapp;
} ContextoReportes;"""

# 2) activar botones despues de "Generar reporte"
A2 = """    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);
}

/* Abre el dialogo estandar"""
N2 = """    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);
    gtk_widget_set_sensitive(ctx->btn_correo, TRUE);
    gtk_widget_set_sensitive(ctx->btn_whatsapp, TRUE);
}

/* Abre el dialogo estandar"""

# 3) activar botones despues de un reporte por categoria
A3 = """    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);

    agregar_entrada_historial(ctx, tipo_txt);"""
N3 = """    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);
    gtk_widget_set_sensitive(ctx->btn_correo, TRUE);
    gtk_widget_set_sensitive(ctx->btn_whatsapp, TRUE);

    agregar_entrada_historial(ctx, tipo_txt);"""

# 4) funciones de envio
A4 = "static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {"
N4 = r"""/* ---- Enviar el reporte en pantalla por correo o WhatsApp ---- */

#define SCRIPT_ENVIO_REPORTE "/usr/local/bin/pawos-enviar-documento"

static gchar *pedir_destino_reporte(GtkWindow *padre, const char *titulo, const char *etiqueta) {
    GtkWidget *d = gtk_dialog_new_with_buttons(titulo, padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Enviar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(d), 400, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(d));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    gtk_box_set_spacing(GTK_BOX(area), 6);
    GtkWidget *lbl = gtk_label_new(etiqueta);
    gtk_label_set_line_wrap(GTK_LABEL(lbl), TRUE);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(area), lbl, FALSE, FALSE, 0);
    GtkWidget *entrada = gtk_entry_new();
    gtk_entry_set_activates_default(GTK_ENTRY(entrada), TRUE);
    gtk_box_pack_start(GTK_BOX(area), entrada, FALSE, FALSE, 0);
    gtk_dialog_set_default_response(GTK_DIALOG(d), GTK_RESPONSE_OK);
    gtk_widget_show_all(d);
    gchar *res = NULL;
    if (gtk_dialog_run(GTK_DIALOG(d)) == GTK_RESPONSE_OK) {
        res = g_strstrip(g_strdup(gtk_entry_get_text(GTK_ENTRY(entrada))));
        if (res[0] == '\0') { g_free(res); res = NULL; }
    }
    gtk_widget_destroy(d);
    return res;
}

static void texto_a_slug_reporte(const char *s, GString *out) {
    gboolean ultimo_guion = TRUE;
    for (const char *p = s; *p; p++) {
        unsigned char c = (unsigned char)*p;
        if (g_ascii_isalnum(c)) {
            g_string_append_c(out, (gchar)g_ascii_tolower(c));
            ultimo_guion = FALSE;
        } else if (!ultimo_guion) {
            g_string_append_c(out, '_');
            ultimo_guion = TRUE;
        }
    }
    while (out->len > 0 && out->str[out->len - 1] == '_')
        g_string_truncate(out, out->len - 1);
}

static void enviar_reporte(ContextoReportes *ctx, const char *canal) {
    GtkWindow *ventana = GTK_WINDOW(ctx->ventana);
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(ctx->vista_texto));
    GtkTextIter ini, fin;
    gtk_text_buffer_get_bounds(buffer, &ini, &fin);
    gchar *texto = gtk_text_buffer_get_text(buffer, &ini, &fin, FALSE);
    if (!texto || strlen(texto) < 10) {
        mostrar_mensaje(ventana, "Genera un reporte primero.", TRUE);
        g_free(texto);
        return;
    }

    /* Titulo y periodo del reporte, para el nombre del archivo y el asunto */
    gchar *titulo = g_strdup("Reporte de PawOS");
    gchar *periodo = NULL;
    gchar **lineas = g_strsplit(texto, "\n", 8);
    for (int i = 0; lineas[i]; i++) {
        if (g_str_has_prefix(lineas[i], "=====")) {
            gchar *t = g_strdup(lineas[i]);
            g_strdelimit(t, "=", ' ');
            g_strstrip(t);
            if (g_str_has_suffix(t, " - PawOS")) t[strlen(t) - 8] = '\0';
            g_free(titulo);
            titulo = t;
        } else if (g_str_has_prefix(lineas[i], "Periodo:")) {
            g_free(periodo);
            periodo = g_strstrip(g_strdup(lineas[i] + 8));
            if (g_str_has_prefix(periodo, "Todos")) { g_free(periodo); periodo = g_strdup("Todos los meses"); }
        }
    }
    g_strfreev(lineas);

    gboolean es_correo = (strcmp(canal, "correo") == 0);
    gchar *destino = pedir_destino_reporte(ventana,
        es_correo ? "Enviar reporte por correo" : "Enviar reporte por WhatsApp",
        es_correo ? "Correo de destino:" :
                    "Numero de WhatsApp (8 digitos, o con codigo de pais):");
    if (!destino) { g_free(texto); g_free(titulo); g_free(periodo); return; }

    if (es_correo) {
        const char *arroba = strchr(destino, '@');
        if (!arroba || arroba == destino || !strchr(arroba, '.')) {
            mostrar_mensaje(ventana, "Ese correo no parece valido.", TRUE);
            g_free(destino); g_free(texto); g_free(titulo); g_free(periodo);
            return;
        }
    } else {
        GString *digitos = g_string_new(NULL);
        for (const char *p = destino; *p; p++)
            if (g_ascii_isdigit(*p)) g_string_append_c(digitos, *p);
        if (digitos->len == 8) g_string_prepend(digitos, "502");
        if (digitos->len < 8) {
            mostrar_mensaje(ventana, "Ese numero de WhatsApp no parece valido.", TRUE);
            g_string_free(digitos, TRUE);
            g_free(destino); g_free(texto); g_free(titulo); g_free(periodo);
            return;
        }
        g_free(destino);
        destino = g_string_free(digitos, FALSE);
    }

    /* PDF temporal con nombre legible: reporte_de_donantes_octubre_2026.pdf */
    GString *slug = g_string_new(NULL);
    texto_a_slug_reporte(titulo, slug);
    if (periodo) {
        g_string_append_c(slug, '_');
        texto_a_slug_reporte(periodo, slug);
    }
    gchar *carpeta_tmp = g_dir_make_tmp("pawos-reporte-XXXXXX", NULL);
    if (!carpeta_tmp) {
        mostrar_mensaje(ventana, "No se pudo preparar el PDF del reporte.", TRUE);
        g_string_free(slug, TRUE);
        g_free(destino); g_free(texto); g_free(titulo); g_free(periodo);
        return;
    }
    gchar *nombre_pdf = g_strdup_printf("%s.pdf", slug->str);
    gchar *ruta_pdf = g_build_filename(carpeta_tmp, nombre_pdf, NULL);
    g_string_free(slug, TRUE);

    gboolean pdf_ok = generar_pdf_reporte_bonito(ruta_pdf, texto)
                      || escribir_pdf_simple(ruta_pdf, texto);
    if (!pdf_ok) {
        mostrar_mensaje(ventana, "No se pudo generar el PDF del reporte.", TRUE);
    } else {
        gchar *asunto = g_strdup_printf("%s%s%s%s", titulo,
                                        periodo ? " (" : "", periodo ? periodo : "", periodo ? ")" : "");
        gchar *mensaje = g_strdup_printf("Adjuntamos el reporte: %s. -- PawOS Refugio", asunto);
        gchar *argv[] = { "sudo", "-n", (gchar *)SCRIPT_ENVIO_REPORTE,
            "--canal", (gchar *)canal, "--destino", destino, "--pdf", ruta_pdf,
            "--asunto", asunto, "--mensaje", mensaje, NULL };
        gchar *salida = NULL, *err = NULL;
        gint estado = 0;
        GError *gerr = NULL;

        gtk_widget_set_sensitive(ctx->ventana, FALSE);
        while (gtk_events_pending()) gtk_main_iteration();
        gboolean lanzado = g_spawn_sync(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL,
                                        &salida, &err, &estado, &gerr);
        gtk_widget_set_sensitive(ctx->ventana, TRUE);

        if (lanzado && estado == 0) {
            gchar *msg = g_strdup_printf("Reporte enviado a %s.", destino);
            mostrar_mensaje(ventana, msg, FALSE);
            g_free(msg);
        } else if (err && (strstr(err, "password is required") || strstr(err, "terminal is required"))) {
            mostrar_mensaje(ventana,
                "Falta instalar el permiso de envio. En una terminal ejecuta:\n"
                "sudo bash instalar-documentos.sh", TRUE);
        } else {
            gchar *detalle = (err && err[0]) ? g_strstrip(g_strndup(err, 300))
                                             : g_strdup(gerr ? gerr->message : "Error desconocido.");
            gchar *msg = g_strdup_printf("No se pudo enviar.\n\n%s", detalle);
            mostrar_mensaje(ventana, msg, TRUE);
            g_free(msg);
            g_free(detalle);
        }
        if (gerr) g_error_free(gerr);
        g_free(salida);
        g_free(err);
        g_free(asunto);
        g_free(mensaje);
    }

    g_remove(ruta_pdf);
    g_rmdir(carpeta_tmp);
    g_free(ruta_pdf);
    g_free(nombre_pdf);
    g_free(carpeta_tmp);
    g_free(destino);
    g_free(texto);
    g_free(titulo);
    g_free(periodo);
}

static void on_enviar_reporte_correo_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    enviar_reporte((ContextoReportes *)datos, "correo");
}

static void on_enviar_reporte_whatsapp_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    enviar_reporte((ContextoReportes *)datos, "whatsapp");
}

static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {"""

# 5) botones en la pantalla (en una fila con "Guardar como")
A5 = """    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);"""
N5 = """    GtkWidget *fila_acciones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(caja), fila_acciones, FALSE, FALSE, 0);

    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(fila_acciones), ctx->btn_guardar, FALSE, FALSE, 0);

    ctx->btn_correo = gtk_button_new_with_label("Enviar por correo");
    gtk_widget_set_sensitive(ctx->btn_correo, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_correo, "Genera un reporte primero para poder enviarlo en PDF.");
    gtk_box_pack_start(GTK_BOX(fila_acciones), ctx->btn_correo, FALSE, FALSE, 0);

    ctx->btn_whatsapp = gtk_button_new_with_label("Enviar por WhatsApp");
    gtk_widget_set_sensitive(ctx->btn_whatsapp, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_whatsapp, "Genera un reporte primero para poder enviarlo en PDF.");
    gtk_box_pack_start(GTK_BOX(fila_acciones), ctx->btn_whatsapp, FALSE, FALSE, 0);"""

# 6) conexion de senales
A6 = """    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);"""
N6 = """    g_signal_connect(ctx->btn_guardar, "clicked", G_CALLBACK(on_guardar_como_reporte_clicked), ctx);
    g_signal_connect(ctx->btn_correo, "clicked", G_CALLBACK(on_enviar_reporte_correo_clicked), ctx);
    g_signal_connect(ctx->btn_whatsapp, "clicked", G_CALLBACK(on_enviar_reporte_whatsapp_clicked), ctx);"""

CAMBIOS = [
    (A1, N1, "contexto de reportes"),
    (A2, N2, "activar botones tras 'Generar reporte'"),
    (A3, N3, "activar botones tras reporte por categoria"),
    (A4, N4, "funciones de envio"),
    (A5, N5, "botones en la pantalla"),
    (A6, N6, "conexion de senales"),
]


def main():
    try:
        with open(GTK_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)
    if "generar_pdf_reporte_bonito" not in contenido:
        print("ERROR: aplica primero parche-reportes-pdf.py.")
        sys.exit(1)
    if "glib/gstdio.h" not in contenido:
        print("ERROR: falta '#include <glib/gstdio.h>' (ver el arreglo con sed del parche de PDF).")
        sys.exit(1)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(GTK_C, GTK_C + ".bak_reportes_enviar")
    print(f"Backup: {GTK_C}.bak_reportes_enviar")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(GTK_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{GTK_C} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
