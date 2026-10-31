/*
 * main_monitor_gui.c - PawOS Monitor
 *
 * App grafica standalone (GTK3) que muestra el estado del sistema
 * (CPU/carga, memoria, swap, disco, tiempo activo, procesos) leyendo
 * directo de /proc y /sys, igual que ya hace servidor_monitoreo.c
 * para su dashboard HTML -- aqui se repite la misma logica de lectura
 * (mismos archivos de /proc, mismos umbrales de color) pero en una
 * ventana GTK nativa con graficas de historial en vivo, sin pasar por
 * HTTP ni necesitar libcurl.
 *
 * No depende de la base de datos de PawOS (no usa db.c): es una
 * utilidad de monitoreo de sistema pura, enfocada solo en recursos
 * (CPU, memoria, swap, disco). Las Alertas de Sensores ya se
 * consultan en Refugio GUI, no se duplican aqui.
 */
#include <gtk/gtk.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <dirent.h>
#include <unistd.h>
#include <sys/statvfs.h>
#include "version.h"

#define INTERVALO_REFRESCO_SEG 2
#define HISTORIAL_MAX 60

typedef struct {
    GtkWidget *ventana;

    GtkWidget *lbl_cpu_pct;
    GtkWidget *lbl_cpu_detalle;
    GtkWidget *grafico_cpu;
    double     historial_cpu[HISTORIAL_MAX];

    GtkWidget *lbl_mem_pct;
    GtkWidget *lbl_mem_detalle;
    GtkWidget *grafico_mem;
    double     historial_mem[HISTORIAL_MAX];

    GtkWidget *lbl_swap_pct;
    GtkWidget *lbl_swap_detalle;
    GtkWidget *grafico_swap;
    double     historial_swap[HISTORIAL_MAX];

    GtkWidget *lbl_disco_pct;
    GtkWidget *lbl_disco_detalle;
    GtkWidget *grafico_disco;
    double     historial_disco[HISTORIAL_MAX];

    GtkWidget *lbl_uptime;
    GtkWidget *lbl_procesos;
} ContextoApp;

/* ---------- Lectura de /proc, identico a servidor_monitoreo.c ---------- */

static double leer_uptime(void) {
    FILE *f = fopen("/proc/uptime", "r");
    double up = 0;
    if (f) { if (fscanf(f, "%lf", &up) != 1) up = 0; fclose(f); }
    return up;
}

static void leer_memoria(long *total_kb, long *disponible_kb) {
    FILE *f = fopen("/proc/meminfo", "r");
    *total_kb = 0; *disponible_kb = 0;
    if (!f) return;
    char linea[256];
    while (fgets(linea, sizeof(linea), f)) {
        if (strncmp(linea, "MemTotal:", 9) == 0) sscanf(linea + 9, "%ld", total_kb);
        else if (strncmp(linea, "MemAvailable:", 13) == 0) sscanf(linea + 13, "%ld", disponible_kb);
    }
    fclose(f);
}

static void leer_swap(long *total_kb, long *usado_kb) {
    FILE *f = fopen("/proc/meminfo", "r");
    long swap_total = 0, swap_free = 0;
    if (f) {
        char linea[256];
        while (fgets(linea, sizeof(linea), f)) {
            if (strncmp(linea, "SwapTotal:", 10) == 0) sscanf(linea + 10, "%ld", &swap_total);
            else if (strncmp(linea, "SwapFree:", 9) == 0) sscanf(linea + 9, "%ld", &swap_free);
        }
        fclose(f);
    }
    *total_kb = swap_total;
    *usado_kb = swap_total - swap_free;
}

static void leer_carga(double *l1, double *l5, double *l15) {
    FILE *f = fopen("/proc/loadavg", "r");
    *l1 = *l5 = *l15 = 0;
    if (f) { if (fscanf(f, "%lf %lf %lf", l1, l5, l15) != 3) { *l1 = *l5 = *l15 = 0; } fclose(f); }
}

static int contar_cpus(void) {
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    return (n > 0) ? (int)n : 1;
}

static void leer_disco(double *usado_gb, double *total_gb) {
    struct statvfs st;
    *usado_gb = 0; *total_gb = 0;
    if (statvfs("/", &st) == 0) {
        double total = (double)st.f_blocks * st.f_frsize;
        double libre = (double)st.f_bfree * st.f_frsize;
        *total_gb = total / (1024.0 * 1024.0 * 1024.0);
        *usado_gb = (total - libre) / (1024.0 * 1024.0 * 1024.0);
    }
}

static int contar_procesos(void) {
    DIR *d = opendir("/proc");
    int contador = 0;
    if (!d) return -1;
    struct dirent *ent;
    while ((ent = readdir(d)) != NULL) {
        int es_numero = 1;
        for (char *p = ent->d_name; *p; p++) {
            if (!isdigit((unsigned char)*p)) { es_numero = 0; break; }
        }
        if (es_numero) contador++;
    }
    closedir(d);
    return contador;
}

/* Mismos umbrales que servidor_monitoreo.c, para que ambos
 * "dashboards" (el HTML y este GTK) coincidan en que color le ponen
 * a un mismo porcentaje. */
static const char *color_por_pct(double pct) {
    if (pct < 60) return "#2ecc71";
    if (pct < 85) return "#f1c40f";
    return "#e74c3c";
}

static void color_rgb_por_pct(double pct, double *r, double *g, double *b) {
    if (pct < 60)      { *r = 0.18; *g = 0.80; *b = 0.44; }   /* verde  #2ecc71 */
    else if (pct < 85) { *r = 0.95; *g = 0.77; *b = 0.06; }   /* amarillo #f1c40f */
    else               { *r = 0.91; *g = 0.30; *b = 0.24; }   /* rojo   #e74c3c */
}

static void formatear_uptime(double segundos, char *buf, size_t len) {
    long total = (long)segundos;
    long dias = total / 86400;
    long horas = (total % 86400) / 3600;
    long min = (total % 3600) / 60;
    if (dias > 0) snprintf(buf, len, "%ld d, %ld h, %ld min", dias, horas, min);
    else if (horas > 0) snprintf(buf, len, "%ld h, %ld min", horas, min);
    else snprintf(buf, len, "%ld min", min);
}

static void set_pct_label(GtkWidget *lbl, double pct) {
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    gchar *markup = g_strdup_printf(
        "<span size='xx-large' weight='bold' foreground='%s'>%.0f%%</span>",
        color_por_pct(pct), pct);
    gtk_label_set_markup(GTK_LABEL(lbl), markup);
    g_free(markup);
}

static void agregar_historial(double *historial, double valor) {
    memmove(historial, historial + 1, (HISTORIAL_MAX - 1) * sizeof(double));
    historial[HISTORIAL_MAX - 1] = valor;
}

/* ---------- Grafica de historial (cairo, dentro de un GtkDrawingArea) --- */

static gboolean on_draw_grafico(GtkWidget *widget, cairo_t *cr, gpointer datos) {
    double *historial = (double *)datos;
    GtkAllocation alloc;
    gtk_widget_get_allocation(widget, &alloc);
    double w = alloc.width, h = alloc.height;

    /* fondo */
    cairo_set_source_rgb(cr, 1, 1, 1);
    cairo_paint(cr);

    /* lineas guia horizontales (0/50/100%), estilo sutil tipo
     * Administrador de tareas */
    cairo_set_source_rgba(cr, 0, 0, 0, 0.07);
    cairo_set_line_width(cr, 1);
    const double niveles[] = {0.0, 50.0, 100.0};
    for (int i = 0; i < 3; i++) {
        double y = h - (h * (niveles[i] / 100.0));
        if (y < 1) y = 1;
        if (y > h - 1) y = h - 1;
        cairo_move_to(cr, 0, y);
        cairo_line_to(cr, w, y);
    }
    cairo_stroke(cr);

    /* ultimo valor valido, para elegir el color de la linea */
    double ultimo = -1;
    for (int i = HISTORIAL_MAX - 1; i >= 0; i--) {
        if (historial[i] >= 0) { ultimo = historial[i]; break; }
    }
    double r = 0.137, g = 0.573, b = 0.294; /* verde de marca por defecto */
    if (ultimo >= 0) color_rgb_por_pct(ultimo, &r, &g, &b);

    /* Construir la curva de datos */
    gboolean hay_datos = FALSE;
    double primer_x = 0, ultimo_x = 0;
    cairo_new_path(cr);
    for (int i = 0; i < HISTORIAL_MAX; i++) {
        double pct = historial[i];
        if (pct < 0) continue;
        double x = (double)i / (HISTORIAL_MAX - 1) * w;
        double y = h - (h * (pct / 100.0));
        if (!hay_datos) { cairo_move_to(cr, x, y); primer_x = x; hay_datos = TRUE; }
        else cairo_line_to(cr, x, y);
        ultimo_x = x;
    }

    if (hay_datos) {
        cairo_path_t *trazo = cairo_copy_path(cr);

        /* Relleno degradado debajo de la curva (look tipo Administrador
         * de tareas de Windows: mas opaco arriba, se desvanece abajo). */
        cairo_line_to(cr, ultimo_x, h);
        cairo_line_to(cr, primer_x, h);
        cairo_close_path(cr);
        cairo_pattern_t *degradado = cairo_pattern_create_linear(0, 0, 0, h);
        cairo_pattern_add_color_stop_rgba(degradado, 0, r, g, b, 0.35);
        cairo_pattern_add_color_stop_rgba(degradado, 1, r, g, b, 0.02);
        cairo_set_source(cr, degradado);
        cairo_fill(cr);
        cairo_pattern_destroy(degradado);

        /* Trazo de la linea, encima del relleno */
        cairo_new_path(cr);
        cairo_append_path(cr, trazo);
        cairo_path_destroy(trazo);
        cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);
        cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
        cairo_set_source_rgb(cr, r, g, b);
        cairo_set_line_width(cr, 2);
        cairo_stroke(cr);
    }
    return FALSE;
}

static gboolean actualizar_metricas(gpointer datos) {
    ContextoApp *ctx = datos;

    /* CPU / carga */
    double l1, l5, l15;
    leer_carga(&l1, &l5, &l15);
    int ncpus = contar_cpus();
    double pct_cpu = (l1 / ncpus) * 100.0;
    if (pct_cpu > 100) pct_cpu = 100;
    set_pct_label(ctx->lbl_cpu_pct, pct_cpu);
    gchar *det_cpu = g_strdup_printf("Carga: %.2f / %.2f / %.2f (%d CPUs)", l1, l5, l15, ncpus);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_cpu_detalle), det_cpu);
    g_free(det_cpu);
    agregar_historial(ctx->historial_cpu, pct_cpu);
    gtk_widget_queue_draw(ctx->grafico_cpu);

    /* Memoria */
    long mem_total, mem_disp;
    leer_memoria(&mem_total, &mem_disp);
    double pct_mem = mem_total > 0 ? (double)(mem_total - mem_disp) / mem_total * 100.0 : 0;
    set_pct_label(ctx->lbl_mem_pct, pct_mem);
    gchar *det_mem = g_strdup_printf("%.1f GB / %.1f GB",
        (mem_total - mem_disp) / (1024.0 * 1024.0), mem_total / (1024.0 * 1024.0));
    gtk_label_set_text(GTK_LABEL(ctx->lbl_mem_detalle), det_mem);
    g_free(det_mem);
    agregar_historial(ctx->historial_mem, pct_mem);
    gtk_widget_queue_draw(ctx->grafico_mem);

    /* Swap */
    long swap_total, swap_usado;
    leer_swap(&swap_total, &swap_usado);
    double pct_swap = swap_total > 0 ? (double)swap_usado / swap_total * 100.0 : 0;
    set_pct_label(ctx->lbl_swap_pct, pct_swap);
    gchar *det_swap = swap_total > 0
        ? g_strdup_printf("%.1f GB / %.1f GB", swap_usado / (1024.0 * 1024.0), swap_total / (1024.0 * 1024.0))
        : g_strdup_printf("Sin swap configurado");
    gtk_label_set_text(GTK_LABEL(ctx->lbl_swap_detalle), det_swap);
    g_free(det_swap);
    agregar_historial(ctx->historial_swap, pct_swap);
    gtk_widget_queue_draw(ctx->grafico_swap);

    /* Disco */
    double disco_usado, disco_total;
    leer_disco(&disco_usado, &disco_total);
    double pct_disco = disco_total > 0 ? (disco_usado / disco_total) * 100.0 : 0;
    set_pct_label(ctx->lbl_disco_pct, pct_disco);
    gchar *det_disco = g_strdup_printf("%.1f GB / %.1f GB", disco_usado, disco_total);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_disco_detalle), det_disco);
    g_free(det_disco);
    agregar_historial(ctx->historial_disco, pct_disco);
    gtk_widget_queue_draw(ctx->grafico_disco);

    /* Tiempo activo y procesos (sin grafica, son valores sin techo fijo) */
    char buf_uptime[64];
    formatear_uptime(leer_uptime(), buf_uptime, sizeof(buf_uptime));
    gtk_label_set_text(GTK_LABEL(ctx->lbl_uptime), buf_uptime);

    int procesos = contar_procesos();
    gchar *txt_procesos = g_strdup_printf("%d", procesos);
    gtk_label_set_text(GTK_LABEL(ctx->lbl_procesos), txt_procesos);
    g_free(txt_procesos);

    return G_SOURCE_CONTINUE; /* seguir repitiendo el temporizador */
}

/* ---------- Interfaz ---------- */

static void aplicar_estilos_simples(void) {
    GtkCssProvider *proveedor = gtk_css_provider_new();
    const char *css =
        "window { background-color: #F4F6F5; }"
        ".pawos-header {"
        "  background-image: linear-gradient(180deg, #23924B 0%, #12451F 100%);"
        "  padding: 16px 20px;"
        "}"
        ".pawos-header label { color: #FFFFFF; }"
        ".pawos-tarjeta {"
        "  background-color: #FFFFFF;"
        "  border-radius: 12px;"
        "  padding: 14px;"
        "  box-shadow: 0 2px 8px rgba(0,0,0,0.10);"
        "}"
        ".pawos-tarjeta-titulo { color: #555555; }";
    gtk_css_provider_load_from_data(proveedor, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(), GTK_STYLE_PROVIDER(proveedor),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(proveedor);
}

static GtkWidget *crear_tarjeta_metrica(const char *titulo, GtkWidget **out_lbl_pct,
                                         GtkWidget **out_lbl_detalle, GtkWidget **out_grafico,
                                         double *historial) {
    GtkWidget *tarjeta = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta), "pawos-tarjeta");
    gtk_widget_set_hexpand(tarjeta, TRUE);

    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf("<span weight='bold' size='small'>%s</span>", titulo);
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_widget_set_halign(lbl_titulo, GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_titulo), "pawos-tarjeta-titulo");
    gtk_box_pack_start(GTK_BOX(tarjeta), lbl_titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_pct = gtk_label_new(NULL);
    gtk_widget_set_halign(lbl_pct, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta), lbl_pct, FALSE, FALSE, 0);

    GtkWidget *lbl_detalle = gtk_label_new(NULL);
    gtk_widget_set_halign(lbl_detalle, GTK_ALIGN_START);
    gtk_widget_set_margin_bottom(lbl_detalle, 6);
    gtk_box_pack_start(GTK_BOX(tarjeta), lbl_detalle, FALSE, FALSE, 0);

    GtkWidget *grafico = gtk_drawing_area_new();
    gtk_widget_set_size_request(grafico, -1, 100);
    g_signal_connect(grafico, "draw", G_CALLBACK(on_draw_grafico), historial);
    gtk_box_pack_start(GTK_BOX(tarjeta), grafico, FALSE, FALSE, 0);

    if (out_lbl_pct) *out_lbl_pct = lbl_pct;
    if (out_lbl_detalle) *out_lbl_detalle = lbl_detalle;
    if (out_grafico) *out_grafico = grafico;
    return tarjeta;
}

static GtkWidget *crear_tarjeta_simple(const char *titulo, GtkWidget **out_lbl_valor) {
    GtkWidget *tarjeta = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta), "pawos-tarjeta");
    gtk_widget_set_hexpand(tarjeta, TRUE);

    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf("<span weight='bold' size='small'>%s</span>", titulo);
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_widget_set_halign(lbl_titulo, GTK_ALIGN_START);
    gtk_style_context_add_class(gtk_widget_get_style_context(lbl_titulo), "pawos-tarjeta-titulo");
    gtk_box_pack_start(GTK_BOX(tarjeta), lbl_titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_valor = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_valor), "<span size='xx-large' weight='bold'>-</span>");
    gtk_widget_set_halign(lbl_valor, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta), lbl_valor, FALSE, FALSE, 0);

    if (out_lbl_valor) *out_lbl_valor = lbl_valor;
    return tarjeta;
}

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS Monitor");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 1000, 620);
    gtk_window_set_position(GTK_WINDOW(ctx->ventana), GTK_WIN_POS_CENTER);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    GtkWidget *encabezado = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "pawos-header");
    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf(
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS Monitor</span>  <span size='small'>v%s</span>",
        PAWOS_VERSION);
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_box_pack_start(GTK_BOX(encabezado), lbl_titulo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), encabezado, FALSE, FALSE, 0);

    GtkWidget *scroll_principal = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_principal),
        GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll_principal, TRUE);
    gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_principal, TRUE, TRUE, 0);

    GtkWidget *contenido = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    gtk_container_set_border_width(GTK_CONTAINER(contenido), 16);
    gtk_container_add(GTK_CONTAINER(scroll_principal), contenido);

    GtkWidget *fila1 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_box_pack_start(GTK_BOX(fila1),
        crear_tarjeta_metrica("CPU (carga promedio)", &ctx->lbl_cpu_pct, &ctx->lbl_cpu_detalle,
                               &ctx->grafico_cpu, ctx->historial_cpu),
        TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(fila1),
        crear_tarjeta_metrica("Memoria", &ctx->lbl_mem_pct, &ctx->lbl_mem_detalle,
                               &ctx->grafico_mem, ctx->historial_mem),
        TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), fila1, FALSE, FALSE, 0);

    GtkWidget *fila2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_box_pack_start(GTK_BOX(fila2),
        crear_tarjeta_metrica("Swap", &ctx->lbl_swap_pct, &ctx->lbl_swap_detalle,
                               &ctx->grafico_swap, ctx->historial_swap),
        TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(fila2),
        crear_tarjeta_metrica("Disco (/)", &ctx->lbl_disco_pct, &ctx->lbl_disco_detalle,
                               &ctx->grafico_disco, ctx->historial_disco),
        TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), fila2, FALSE, FALSE, 0);

    GtkWidget *fila3 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 12);
    gtk_box_pack_start(GTK_BOX(fila3), crear_tarjeta_simple("Tiempo activo", &ctx->lbl_uptime), TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(fila3), crear_tarjeta_simple("Procesos", &ctx->lbl_procesos), TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), fila3, FALSE, FALSE, 0);

    gtk_widget_show_all(ctx->ventana);
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);

    aplicar_estilos_simples();

    ContextoApp ctx;
    memset(&ctx, 0, sizeof(ctx));
    for (int i = 0; i < HISTORIAL_MAX; i++) {
        ctx.historial_cpu[i] = -1;
        ctx.historial_mem[i] = -1;
        ctx.historial_swap[i] = -1;
        ctx.historial_disco[i] = -1;
    }

    construir_ventana(&ctx);
    actualizar_metricas(&ctx);
    g_timeout_add_seconds(INTERVALO_REFRESCO_SEG, actualizar_metricas, &ctx);

    gtk_main();
    return 0;
}
