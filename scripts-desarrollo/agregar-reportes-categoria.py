#!/usr/bin/env python3
# agregar-reportes-categoria.py
#
# Agrega, dentro de la pantalla de Reportes:
#   1) 5 botones para generar un reporte de cada categoria (Mascotas,
#      Vacunas, Adopciones, Donantes, Alertas de Sensores) sin quitar
#      el boton general "Generar reporte" que ya existia.
#   2) Un historial (bitacora) con fecha y hora de cada reporte
#      generado, que persiste entre sesiones (se guarda en un archivo
#      en disco y se recarga cada vez que se abre la pantalla).
#   3) Arregla el bug de "Guardar como .pdf" que en realidad guardaba
#      en .txt: el nombre sugerido por defecto ("reporte_pawos.txt")
#      no se actualizaba al cambiar el filtro a PDF, asi que el
#      archivo final se quedaba con extension .txt aunque el contenido
#      fuera PDF. Ahora la extension SIEMPRE se normaliza segun el
#      formato elegido.
#
# No se toca ninguna otra logica existente. Hace backup .bak de cada
# archivo antes de tocarlo y aborta sin escribir nada si algun bloque
# esperado no se encuentra (para no arriesgar el archivo real).

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
            print("No se modifico nada. Bloque buscado:")
            print("----")
            print(viejo)
            print("----")
            sys.exit(1)
        contenido = contenido.replace(viejo, nuevo, 1)

    shutil.copyfile(ruta, ruta + ".bak")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"  [{nombre}] parchado OK (backup en {ruta}.bak)")


# ============================================================
# 1) include/db.h - declarar las 5 funciones nuevas
# ============================================================

DBH_VIEJO = '''/* ---------- Reportes ---------- */
int reporte_generar(const char *ruta_salida);

#endif'''

DBH_NUEVO = '''/* ---------- Reportes ---------- */
int reporte_generar(const char *ruta_salida);
int reporte_generar_mascotas(const char *ruta_salida);
int reporte_generar_vacunas(const char *ruta_salida);
int reporte_generar_adopciones(const char *ruta_salida);
int reporte_generar_donantes(const char *ruta_salida);
int reporte_generar_alertas(const char *ruta_salida);

#endif'''

parchar("include/db.h",
        [("reporte_generar_mascotas(const char", DBH_VIEJO, DBH_NUEVO)],
        "db.h")


# ============================================================
# 2) src/db.c - agregar las 5 funciones al final del archivo
# ============================================================

DBC_MARCADOR = "int reporte_generar_mascotas(const char *ruta_salida) {"

DBC_NUEVO = '''

/* ---------------- Reportes por categoria (agregado) ---------------- */

int reporte_generar_mascotas(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte de Mascotas - PawOS =====\\n");
    fprintf(f, "Generado: %s\\n\\n", fecha);

    Mascota *ms; int nm;
    mascota_listar(&ms, &nm);
    int disponibles = 0, adoptados = 0, en_proceso = 0, tratamiento = 0;
    for (int i = 0; i < nm; i++) {
        if (!strcmp(ms[i].estado, "disponible")) disponibles++;
        else if (!strcmp(ms[i].estado, "adoptado")) adoptados++;
        else if (!strcmp(ms[i].estado, "en_proceso")) en_proceso++;
        else if (!strcmp(ms[i].estado, "tratamiento")) tratamiento++;
    }
    fprintf(f, "Total registradas : %d\\n", nm);
    fprintf(f, "Disponibles        : %d\\n", disponibles);
    fprintf(f, "En proceso adopcion: %d\\n", en_proceso);
    fprintf(f, "Adoptadas          : %d\\n", adoptados);
    fprintf(f, "En tratamiento     : %d\\n\\n", tratamiento);

    fprintf(f, "-- Detalle --\\n");
    for (int i = 0; i < nm; i++) {
        fprintf(f, "  #%d %s - %s (%s), %d anios, estado: %s, ingreso: %s\\n",
                ms[i].id, ms[i].nombre, ms[i].especie, ms[i].raza, ms[i].edad,
                ms[i].estado, ms[i].fecha_ingreso);
    }
    free(ms);

    fclose(f);
    return 0;
}

int reporte_generar_vacunas(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte de Vacunas - PawOS =====\\n");
    fprintf(f, "Generado: %s\\n\\n", fecha);

    Vacuna *v; int nv;
    vacuna_listar(&v, &nv);
    fprintf(f, "Total de vacunas registradas: %d\\n\\n", nv);
    fprintf(f, "-- Detalle --\\n");
    for (int i = 0; i < nv; i++) {
        fprintf(f, "  Mascota #%d - %s | aplicada: %s | proxima: %s%s%s\\n",
                v[i].mascota_id, v[i].nombre_vacuna, v[i].fecha_aplicacion, v[i].fecha_proxima,
                v[i].observaciones[0] ? " | obs: " : "", v[i].observaciones[0] ? v[i].observaciones : "");
    }
    free(v);

    fclose(f);
    return 0;
}

int reporte_generar_adopciones(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte de Adopciones - PawOS =====\\n");
    fprintf(f, "Generado: %s\\n\\n", fecha);

    Adopcion *a; int na;
    adopcion_listar(&a, &na);
    fprintf(f, "Total de adopciones registradas: %d\\n\\n", na);
    fprintf(f, "-- Detalle --\\n");
    for (int i = 0; i < na; i++) {
        fprintf(f, "  Mascota #%d -> %s (contacto: %s), fecha: %s\\n",
                a[i].mascota_id, a[i].adoptante_nombre, a[i].adoptante_contacto, a[i].fecha_adopcion);
    }
    free(a);

    fclose(f);
    return 0;
}

int reporte_generar_donantes(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte de Donantes - PawOS =====\\n");
    fprintf(f, "Generado: %s\\n\\n", fecha);

    Donante *d; int nd;
    donante_listar(&d, &nd);
    double total = donante_total_recaudado();
    fprintf(f, "Total de donantes registrados: %d\\n", nd);
    fprintf(f, "Total recaudado: %.2f\\n\\n", total);
    fprintf(f, "-- Detalle --\\n");
    for (int i = 0; i < nd; i++) {
        fprintf(f, "  %s (contacto: %s) - Q%.2f - fecha: %s\\n",
                d[i].nombre, d[i].contacto, d[i].monto, d[i].fecha);
    }
    free(d);

    fclose(f);
    return 0;
}

int reporte_generar_alertas(const char *ruta_salida) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    fprintf(f, "===== Reporte de Alertas de Sensores - PawOS =====\\n");
    fprintf(f, "Generado: %s\\n\\n", fecha);

    Alerta *al; int nal;
    alerta_listar(&al, &nal);
    int pendientes = 0;
    for (int i = 0; i < nal; i++) if (!al[i].atendida) pendientes++;
    fprintf(f, "Total de alertas registradas: %d\\n", nal);
    fprintf(f, "Pendientes: %d\\n\\n", pendientes);
    fprintf(f, "-- Detalle --\\n");
    for (int i = 0; i < nal; i++) {
        fprintf(f, "  [%s] animal %s - %s: %s (valor: %.2f) - %s\\n",
                al[i].fecha_hora, al[i].animal_id, al[i].tipo, al[i].detalle, al[i].valor,
                al[i].atendida ? "atendida" : "pendiente");
    }
    free(al);

    fclose(f);
    return 0;
}
'''

with open("src/db.c", "r", encoding="utf-8") as f:
    dbc = f.read()

if DBC_MARCADOR in dbc:
    print("  [db.c] ya estaba aplicado, se omite.")
else:
    shutil.copyfile("src/db.c", "src/db.c.bak")
    with open("src/db.c", "a", encoding="utf-8") as f:
        f.write(DBC_NUEVO)
    print("  [db.c] parchado OK (backup en src/db.c.bak)")


# ============================================================
# 3) src/main_gtk.c
# ============================================================

# 3a) agregar campo vista_historial a ContextoReportes
MGC_STRUCT_VIEJO = '''typedef struct {
    GtkWidget *ventana;
    GtkWidget *vista_texto;
    GtkWidget *lbl_estado;
    GtkWidget *btn_guardar;
} ContextoReportes;'''

MGC_STRUCT_NUEVO = '''typedef struct {
    GtkWidget *ventana;
    GtkWidget *vista_texto;
    GtkWidget *vista_historial;
    GtkWidget *lbl_estado;
    GtkWidget *btn_guardar;
} ContextoReportes;'''

# 3b) arreglar el bug de la extension .pdf/.txt
MGC_BUG_VIEJO = '''    gchar *ruta_final = ruta_elegida;
    if (!g_str_has_suffix(ruta_elegida, ".pdf") && !g_str_has_suffix(ruta_elegida, ".txt")) {
        ruta_final = g_strconcat(ruta_elegida, quiere_pdf ? ".pdf" : ".txt", NULL);
        g_free(ruta_elegida);
    }'''

MGC_BUG_NUEVO = '''    /* Siempre normalizamos la extension segun el formato elegido, sin
     * importar la extension del nombre sugerido por el dialogo. Antes,
     * si el usuario elegia el filtro PDF pero no cambiaba el nombre
     * por defecto "reporte_pawos.txt", el archivo se guardaba con
     * extension .txt aunque el contenido fuera PDF (por eso "no
     * funcionaba" el boton de PDF). */
    gchar *ruta_sin_extension = g_strdup(ruta_elegida);
    if (g_str_has_suffix(ruta_sin_extension, ".pdf") || g_str_has_suffix(ruta_sin_extension, ".txt")) {
        ruta_sin_extension[strlen(ruta_sin_extension) - 4] = '\\0';
    }
    gchar *ruta_final = g_strconcat(ruta_sin_extension, quiere_pdf ? ".pdf" : ".txt", NULL);
    g_free(ruta_sin_extension);
    g_free(ruta_elegida);'''

# 3c) insertar historial + reportes por categoria, antes de abrir_pantalla_reportes
MGC_FUNCS_VIEJO = "static void abrir_pantalla_reportes(GtkWidget *padre, Rol rol) {"

MGC_FUNCS_NUEVO = '''/* ---- Historial de reportes generados (bitacora persistente) ---- */

static void cargar_historial(ContextoReportes *ctx) {
    const char *rutas[2] = { "/var/pawos/reportes/historial_reportes.log", "historial_reportes.log" };
    FILE *f = NULL;
    for (int i = 0; i < 2 && f == NULL; i++) f = fopen(rutas[i], "r");

    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(ctx->vista_historial));
    if (!f) {
        gtk_text_buffer_set_text(buffer, "Todavia no hay reportes registrados.", -1);
        return;
    }

    GPtrArray *lineas = g_ptr_array_new_with_free_func(g_free);
    char linea[256];
    while (fgets(linea, sizeof(linea), f) != NULL) {
        g_ptr_array_add(lineas, g_strdup(linea));
    }
    fclose(f);

    GString *texto = g_string_new(NULL);
    if (lineas->len == 0) {
        g_string_append(texto, "Todavia no hay reportes registrados.");
    } else {
        for (int i = (int)lineas->len - 1; i >= 0; i--) {
            g_string_append(texto, (const char *)g_ptr_array_index(lineas, i));
        }
    }
    gtk_text_buffer_set_text(buffer, texto->str, -1);
    g_string_free(texto, TRUE);
    g_ptr_array_free(lineas, TRUE);
}

static void agregar_entrada_historial(ContextoReportes *ctx, const char *tipo) {
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    char linea[256];
    snprintf(linea, sizeof(linea), "%s - Reporte de %s\\n", fecha, tipo);

    FILE *f = fopen("/var/pawos/reportes/historial_reportes.log", "a");
    if (!f) f = fopen("historial_reportes.log", "a");
    if (f) {
        fputs(linea, f);
        fclose(f);
    }

    cargar_historial(ctx);
}

/* ---- Reportes individuales por categoria ---- */

typedef struct {
    ContextoReportes *ctx;
    const char *nombre_tipo;
    int (*generador)(const char *ruta_salida);
    const char *ruta_fija;
    const char *ruta_relativa;
} DatosReporteCategoria;

static void on_generar_reporte_categoria_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosReporteCategoria *d = (DatosReporteCategoria *)datos;
    ContextoReportes *ctx = d->ctx;

    const char *ruta_usada = NULL;
    if (d->generador(d->ruta_fija) == 0) {
        ruta_usada = d->ruta_fija;
    } else if (d->generador(d->ruta_relativa) == 0) {
        ruta_usada = d->ruta_relativa;
    }

    if (ruta_usada == NULL) {
        char msg[200];
        snprintf(msg, sizeof(msg), "No se pudo generar el reporte de %s.", d->nombre_tipo);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, TRUE);
        return;
    }

    char estado_txt[220];
    snprintf(estado_txt, sizeof(estado_txt), "Reporte de %s generado en: %s", d->nombre_tipo, ruta_usada);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_estado), estado_txt);
    mostrar_contenido_archivo(GTK_TEXT_VIEW(ctx->vista_texto), ruta_usada);
    gtk_widget_set_sensitive(ctx->btn_guardar, TRUE);

    agregar_entrada_historial(ctx, d->nombre_tipo);
}

static void abrir_pantalla_reportes(GtkWidget *padre, Rol rol) {'''

# 3d) agregar los 5 botones de categoria despues del boton "Guardar como"
MGC_BOTONES_VIEJO = '''    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
    gtk_widget_set_halign(ctx->btn_guardar, GTK_ALIGN_START);
    gtk_widget_set_sensitive(ctx->btn_guardar, FALSE);
    gtk_widget_set_tooltip_text(ctx->btn_guardar, "Genera un reporte primero para poder guardarlo donde quieras.");
    gtk_box_pack_start(GTK_BOX(caja), ctx->btn_guardar, FALSE, FALSE, 0);

    ctx->lbl_estado = gtk_label_new("Todavia no se ha generado ningun reporte en esta sesion.");'''

MGC_BOTONES_NUEVO = '''    ctx->btn_guardar = gtk_button_new_with_label("Guardar como (.txt / .pdf)...");
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

    ctx->lbl_estado = gtk_label_new("Todavia no se ha generado ningun reporte en esta sesion.");'''

# 3e) agregar la seccion de historial visible, antes del boton Cerrar
MGC_HIST_VIEJO = '''    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->vista_texto);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");'''

MGC_HIST_NUEVO = '''    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
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

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");'''

parchar("src/main_gtk.c", [
    ("GtkWidget *vista_historial;", MGC_STRUCT_VIEJO, MGC_STRUCT_NUEVO),
    ("ruta_sin_extension", MGC_BUG_VIEJO, MGC_BUG_NUEVO),
    ("DatosReporteCategoria {", MGC_FUNCS_VIEJO, MGC_FUNCS_NUEVO),
    ("caja_categorias", MGC_BOTONES_VIEJO, MGC_BOTONES_NUEVO),
    ("vista_historial = gtk_text_view_new", MGC_HIST_VIEJO, MGC_HIST_NUEVO),
], "main_gtk.c")

print("")
print("Listo. Ahora compila con: make gui")
