#!/usr/bin/env python3
# mejorar-diseno-pdf-y-version.py
#
# 1) Sube la version a 1.1 (include/version.h).
# 2) Mejora el diseno del PDF generado en Reportes: titulo centrado en
#    verde institucional con linea debajo, encabezados de seccion en
#    negrita, fecha en cursiva gris, y un pie de pagina con "PawOS
#    Refugio" + numero de pagina. El .txt no cambia (sigue igual de
#    simple), solo se mejora como se ve el PDF.
#
# No toca ninguna otra logica. Hace backup .bak y aborta sin escribir
# nada si algun bloque esperado no se encuentra.

import shutil
import sys

def parchar(ruta, reemplazos, nombre):
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    for marcador, viejo, nuevo in reemplazos:
        if marcador in contenido:
            print(f"  [{nombre}] '{marcador}' ya estaba aplicado, se omite.")
            continue
        if viejo not in contenido:
            print(f"ERROR [{nombre}]: no se encontro el bloque esperado para '{marcador}'.")
            print("No se modifico nada.")
            sys.exit(1)
        contenido = contenido.replace(viejo, nuevo, 1)

    shutil.copyfile(ruta, ruta + ".bak")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"  [{nombre}] parchado OK (backup en {ruta}.bak)")


# ============================================================
# 1) include/version.h -> 1.1
# ============================================================

parchar("include/version.h", [
    ('#define PAWOS_VERSION "1.1"',
     '#define PAWOS_VERSION "1.0"',
     '#define PAWOS_VERSION "1.1"'),
], "version.h")


# ============================================================
# 2) src/main_gtk.c -> escribir_pdf_simple con diseno profesional
# ============================================================

MGC_PDF_VIEJO = '''static gboolean escribir_pdf_simple(const char *ruta, const char *contenido) {
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
}'''

MGC_PDF_NUEVO = '''static void dibujar_pie_pagina(cairo_t *cr, double ancho, double alto, double margen, int pagina) {
    cairo_save(cr);
    cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
    cairo_set_font_size(cr, 8.0);
    cairo_set_source_rgb(cr, 0.55, 0.55, 0.55);

    cairo_move_to(cr, margen, alto - 20.0);
    cairo_show_text(cr, "PawOS Refugio");

    char texto_pagina[32];
    snprintf(texto_pagina, sizeof(texto_pagina), "Pagina %d", pagina);
    cairo_text_extents_t ext;
    cairo_text_extents(cr, texto_pagina, &ext);
    cairo_move_to(cr, ancho - margen - ext.width, alto - 20.0);
    cairo_show_text(cr, texto_pagina);

    cairo_restore(cr);
}

/* Escribe el reporte con un diseno mas profesional: el titulo
 * ("===== ... =====") se centra en verde institucional con una linea
 * debajo, la fecha de generacion sale en cursiva gris, los encabezados
 * de seccion ("-- ... --") salen en negrita, y cada pagina lleva un
 * pie con el nombre del sistema y el numero de pagina. El resto del
 * contenido sigue en monoespaciado, igual que antes. */
static gboolean escribir_pdf_simple(const char *ruta, const char *contenido) {
    const double ancho = 612.0, alto = 792.0; /* carta (Letter), en puntos */
    const double margen = 40.0;
    const double tam_fuente = 10.0;
    const double interlineado = 14.0;
    const double vr = 0.137, vg = 0.573, vb = 0.294; /* verde institucional PawOS */

    cairo_surface_t *superficie = cairo_pdf_surface_create(ruta, ancho, alto);
    if (cairo_surface_status(superficie) != CAIRO_STATUS_SUCCESS) {
        cairo_surface_destroy(superficie);
        return FALSE;
    }
    cairo_t *cr = cairo_create(superficie);

    int pagina = 1;
    double y = margen;

    gchar **lineas = g_strsplit(contenido, "\\n", -1);
    for (int i = 0; lineas[i] != NULL; i++) {
        const char *linea = lineas[i];
        gboolean es_titulo = g_str_has_prefix(linea, "=====");
        gboolean es_encabezado = strlen(linea) > 4 && g_str_has_prefix(linea, "--") && g_str_has_suffix(linea, "--");
        gboolean es_fecha = g_str_has_prefix(linea, "Generado:");

        double alto_linea = interlineado;
        if (es_titulo) alto_linea = 26.0;
        else if (es_encabezado) alto_linea = 20.0;

        if (y + alto_linea > alto - margen) {
            dibujar_pie_pagina(cr, ancho, alto, margen, pagina);
            cairo_show_page(cr);
            pagina++;
            y = margen;
        }

        if (es_titulo) {
            gchar *texto = g_strdup(linea);
            g_strdelimit(texto, "=", ' ');
            gchar *texto_limpio = g_strstrip(texto);

            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 16.0);
            cairo_set_source_rgb(cr, vr, vg, vb);
            cairo_text_extents_t ext;
            cairo_text_extents(cr, texto_limpio, &ext);
            cairo_move_to(cr, (ancho - ext.width) / 2.0, y + 16.0);
            cairo_show_text(cr, texto_limpio);

            cairo_set_line_width(cr, 1.2);
            cairo_move_to(cr, margen, y + 24.0);
            cairo_line_to(cr, ancho - margen, y + 24.0);
            cairo_stroke(cr);

            g_free(texto);
            y += alto_linea;
        } else if (es_fecha) {
            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_ITALIC, CAIRO_FONT_WEIGHT_NORMAL);
            cairo_set_font_size(cr, 9.0);
            cairo_set_source_rgb(cr, 0.4, 0.4, 0.4);
            cairo_text_extents_t ext;
            cairo_text_extents(cr, linea, &ext);
            cairo_move_to(cr, (ancho - ext.width) / 2.0, y + 10.0);
            cairo_show_text(cr, linea);
            y += alto_linea;
        } else if (es_encabezado) {
            gchar *texto = g_strdup(linea);
            g_strdelimit(texto, "-", ' ');
            gchar *texto_limpio = g_strstrip(texto);

            cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD);
            cairo_set_font_size(cr, 11.5);
            cairo_set_source_rgb(cr, vr * 0.7, vg * 0.7, vb * 0.7);
            cairo_move_to(cr, margen, y + 14.0);
            cairo_show_text(cr, texto_limpio);

            g_free(texto);
            y += alto_linea;
        } else if (linea[0] == '\\0') {
            y += alto_linea * 0.6;
        } else {
            cairo_select_font_face(cr, "Monospace", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
            cairo_set_font_size(cr, tam_fuente);
            cairo_set_source_rgb(cr, 0.1, 0.1, 0.1);
            cairo_move_to(cr, margen, y + 9.0);
            cairo_show_text(cr, linea);
            y += alto_linea;
        }
    }
    g_strfreev(lineas);

    dibujar_pie_pagina(cr, ancho, alto, margen, pagina);
    cairo_show_page(cr);
    cairo_status_t estado = cairo_status(cr);
    cairo_destroy(cr);
    cairo_surface_destroy(superficie);
    return estado == CAIRO_STATUS_SUCCESS;
}'''

parchar("src/main_gtk.c", [
    ("dibujar_pie_pagina", MGC_PDF_VIEJO, MGC_PDF_NUEVO),
], "main_gtk.c")

print("")
print("Listo. Ahora compila con: make gui")
