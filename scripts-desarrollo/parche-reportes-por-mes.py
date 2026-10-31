#!/usr/bin/env python3
"""
parche-reportes-por-mes.py   (despues de parche-reporte-donantes-mes.py)

Reportes -> botones Vacunas, Adopciones y Alertas de Sensores: igual que
Donantes, antes de generar preguntan POR QUE MES (o "Todos los meses",
agrupado por mes con subtotales y total general).

  - Vacunas:    se agrupa por fecha de aplicacion.
  - Adopciones: por fecha de adopcion.
  - Alertas:    por fecha de la alerta (y cuenta cuantas siguen pendientes).

Mascotas no cambia (es un estado actual, no tiene fecha de movimiento).
No se tocan los reportes originales; se agregan funciones nuevas.

Uso (parado en la raiz del repo):
    python3 parche-reportes-por-mes.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
MARCA = "reporte_generar_mensual"

# ------------------------------------------------------------------ db.h
H_VIEJO = "int reporte_generar_donantes_mes(const char *ruta_salida, const char *mes);"
H_NUEVO = """int reporte_generar_donantes_mes(const char *ruta_salida, const char *mes);
/* Reportes por mes de vacunas / adopciones / alertas. mes = "AAAA-MM" o NULL/"" = todos. */
#define REPORTE_VACUNAS    1
#define REPORTE_ADOPCIONES 2
#define REPORTE_ALERTAS    3
int reporte_generar_mensual(const char *ruta_salida, int tipo, const char *mes);
/* Meses ("AAAA-MM", el mas reciente primero) que tienen registros. Devuelve cuantos. */
int reporte_listar_meses(int tipo, char (*meses)[8], int max);"""

# ------------------------------------------------------------------ db.c
C_VIEJO = "static int cmp_donante_fecha(const void *a, const void *b) {"
C_NUEVO = r"""/* ---- Reportes por mes (vacunas, adopciones, alertas) ---- */

typedef struct {
    char fecha[24];
    char linea[420];
    int  pendiente;
} EntradaReporte;

static int cmp_entrada_reporte(const void *a, const void *b) {
    const EntradaReporte *x = a, *y = b;
    int c = strcmp(x->fecha, y->fecha);
    return c ? c : strcmp(x->linea, y->linea);
}

static int cargar_entradas_reporte(int tipo, EntradaReporte **out, int *n) {
    *out = NULL; *n = 0;
    if (tipo == REPORTE_VACUNAS) {
        Vacuna *v = NULL; int nv = 0;
        if (vacuna_listar(&v, &nv) != 0) return -1;
        EntradaReporte *e = calloc((size_t)nv + 1, sizeof(EntradaReporte));
        for (int i = 0; i < nv; i++) {
            snprintf(e[i].fecha, sizeof(e[i].fecha), "%s", v[i].fecha_aplicacion);
            snprintf(e[i].linea, sizeof(e[i].linea),
                     "  Mascota #%d - %s | aplicada: %s | proxima: %s%s%s",
                     v[i].mascota_id, v[i].nombre_vacuna, v[i].fecha_aplicacion, v[i].fecha_proxima,
                     v[i].observaciones[0] ? " | obs: " : "", v[i].observaciones[0] ? v[i].observaciones : "");
        }
        free(v); *out = e; *n = nv;
        return 0;
    }
    if (tipo == REPORTE_ADOPCIONES) {
        Adopcion *a = NULL; int na = 0;
        if (adopcion_listar(&a, &na) != 0) return -1;
        EntradaReporte *e = calloc((size_t)na + 1, sizeof(EntradaReporte));
        for (int i = 0; i < na; i++) {
            snprintf(e[i].fecha, sizeof(e[i].fecha), "%s", a[i].fecha_adopcion);
            snprintf(e[i].linea, sizeof(e[i].linea),
                     "  Mascota #%d -> %s (contacto: %s), fecha: %s",
                     a[i].mascota_id, a[i].adoptante_nombre, a[i].adoptante_contacto, a[i].fecha_adopcion);
        }
        free(a); *out = e; *n = na;
        return 0;
    }
    if (tipo == REPORTE_ALERTAS) {
        Alerta *al = NULL; int nal = 0;
        if (alerta_listar(&al, &nal) != 0) return -1;
        EntradaReporte *e = calloc((size_t)nal + 1, sizeof(EntradaReporte));
        for (int i = 0; i < nal; i++) {
            snprintf(e[i].fecha, sizeof(e[i].fecha), "%s", al[i].fecha_hora);
            snprintf(e[i].linea, sizeof(e[i].linea),
                     "  [%s] animal %s - %s: %s (valor: %.2f) - %s",
                     al[i].fecha_hora, al[i].animal_id, al[i].tipo, al[i].detalle, al[i].valor,
                     al[i].atendida ? "atendida" : "pendiente");
            e[i].pendiente = !al[i].atendida;
        }
        free(al); *out = e; *n = nal;
        return 0;
    }
    return -1;
}

int reporte_listar_meses(int tipo, char (*meses)[8], int max) {
    EntradaReporte *e = NULL; int n = 0;
    if (cargar_entradas_reporte(tipo, &e, &n) != 0) return 0;
    int nm = 0;
    for (int i = 0; i < n && nm < max; i++) {
        if (strlen(e[i].fecha) < 7) continue;
        char ym[8];
        memcpy(ym, e[i].fecha, 7); ym[7] = '\0';
        int ya = 0;
        for (int k = 0; k < nm; k++) if (strcmp(meses[k], ym) == 0) { ya = 1; break; }
        if (!ya) { memcpy(meses[nm], ym, 8); nm++; }
    }
    free(e);
    for (int a = 0; a < nm; a++)
        for (int b = a + 1; b < nm; b++)
            if (strcmp(meses[a], meses[b]) < 0) {
                char tmp[8]; memcpy(tmp, meses[a], 8);
                memcpy(meses[a], meses[b], 8); memcpy(meses[b], tmp, 8);
            }
    return nm;
}

int reporte_generar_mensual(const char *ruta_salida, int tipo, const char *mes) {
    const char *titulo, *unidad;
    if (tipo == REPORTE_VACUNAS)         { titulo = "Vacunas";               unidad = "vacuna(s)"; }
    else if (tipo == REPORTE_ADOPCIONES) { titulo = "Adopciones";            unidad = "adopcion(es)"; }
    else if (tipo == REPORTE_ALERTAS)    { titulo = "Alertas de Sensores";   unidad = "alerta(s)"; }
    else return -1;

    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    int un_mes = (mes && mes[0]);
    char legible[40] = "";
    if (un_mes) reporte_mes_legible(mes, legible, (int)sizeof(legible));

    fprintf(f, "===== Reporte de %s - PawOS =====\n", titulo);
    fprintf(f, "Periodo: %s\n", un_mes ? legible : "Todos los meses (agrupado por mes)");
    fprintf(f, "Generado: %s\n\n", fecha);

    EntradaReporte *e = NULL; int n = 0;
    if (cargar_entradas_reporte(tipo, &e, &n) != 0) { e = NULL; n = 0; }
    if (n > 1) qsort(e, (size_t)n, sizeof(EntradaReporte), cmp_entrada_reporte);

    char mes_actual[8] = "";
    int abierto = 0, cant_mes = 0, pend_mes = 0, cant_total = 0, pend_total = 0;

    for (int i = 0; i < n; i++) {
        char ym[8] = "";
        if (strlen(e[i].fecha) >= 7) { memcpy(ym, e[i].fecha, 7); ym[7] = '\0'; }
        if (un_mes && strcmp(ym, mes) != 0) continue;

        if (!un_mes && (!abierto || strcmp(ym, mes_actual) != 0)) {
            if (abierto) {
                fprintf(f, "  Subtotal: %d %s", cant_mes, unidad);
                if (tipo == REPORTE_ALERTAS) fprintf(f, " - pendientes: %d", pend_mes);
                fprintf(f, "\n\n");
            }
            char etiqueta[40];
            reporte_mes_legible(ym, etiqueta, (int)sizeof(etiqueta));
            fprintf(f, "== %s ==\n", ym[0] ? etiqueta : "Sin fecha");
            snprintf(mes_actual, sizeof(mes_actual), "%s", ym);
            cant_mes = 0; pend_mes = 0; abierto = 1;
        }

        fprintf(f, "%s\n", e[i].linea);
        cant_mes++; cant_total++;
        if (e[i].pendiente) { pend_mes++; pend_total++; }
    }
    if (abierto) {
        fprintf(f, "  Subtotal: %d %s", cant_mes, unidad);
        if (tipo == REPORTE_ALERTAS) fprintf(f, " - pendientes: %d", pend_mes);
        fprintf(f, "\n\n");
    }

    if (cant_total == 0) {
        fprintf(f, "No hay registros en este periodo.\n");
    } else {
        fprintf(f, "%s: %d %s", un_mes ? "TOTAL DEL MES" : "TOTAL GENERAL", cant_total, unidad);
        if (tipo == REPORTE_ALERTAS) fprintf(f, " - pendientes: %d", pend_total);
        fprintf(f, "\n");
    }

    free(e);
    fclose(f);
    return 0;
}

static int cmp_donante_fecha(const void *a, const void *b) {"""

# ------------------------------------------------------------------ main_gtk.c
G_A1 = r"""static int generar_reporte_categoria(DatosReporteCategoria *d, gboolean es_donantes,
                                     const char *mes, const char *ruta) {
    return es_donantes ? reporte_generar_donantes_mes(ruta, mes) : d->generador(ruta);
}
"""
G_N1 = r"""/* Igual que pedir_mes_donantes pero para vacunas, adopciones y alertas. */
static gboolean pedir_mes_reporte(GtkWindow *padre, int tipo, const char *titulo_tipo,
                                  char *out, size_t n_out) {
    char meses[120][8];
    int nm = reporte_listar_meses(tipo, meses, 120);

    char titulo_dlg[96];
    snprintf(titulo_dlg, sizeof(titulo_dlg), "Reporte de %s", titulo_tipo);
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        titulo_dlg, padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Generar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
    GtkWidget *lbl = gtk_label_new("De que mes quieres el reporte?");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl, FALSE, FALSE, 0);
    GtkWidget *combo = gtk_combo_box_text_new();
    for (int i = 0; i < nm; i++) {
        char legible[40];
        reporte_mes_legible(meses[i], legible, (int)sizeof(legible));
        gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), meses[i], legible);
    }
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "", "Todos los meses (agrupado por mes)");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
    gtk_box_pack_start(GTK_BOX(caja), combo, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_widget_show_all(dlg);

    gboolean ok = (gtk_dialog_run(GTK_DIALOG(dlg)) == GTK_RESPONSE_OK);
    if (ok) {
        const gchar *id = gtk_combo_box_get_active_id(GTK_COMBO_BOX(combo));
        snprintf(out, n_out, "%s", id ? id : "");
    }
    gtk_widget_destroy(dlg);
    return ok;
}

static int generar_reporte_categoria(DatosReporteCategoria *d, gboolean es_donantes, int tipo_mes,
                                     const char *mes, const char *ruta) {
    if (es_donantes) return reporte_generar_donantes_mes(ruta, mes);
    if (tipo_mes) return reporte_generar_mensual(ruta, tipo_mes, mes);
    return d->generador(ruta);
}
"""

G_A2 = r"""    char mes_sel[8] = "";
    gboolean es_donantes = (d->generador == reporte_generar_donantes);
    if (es_donantes && !pedir_mes_donantes(GTK_WINDOW(ctx->ventana), mes_sel, sizeof(mes_sel)))
        return;
    char tipo_txt[96];
    snprintf(tipo_txt, sizeof(tipo_txt), "%s", d->nombre_tipo);
    if (es_donantes && mes_sel[0]) {
        char legible[40];
        reporte_mes_legible(mes_sel, legible, (int)sizeof(legible));
        snprintf(tipo_txt, sizeof(tipo_txt), "Donantes (%s)", legible);
    }

    const char *ruta_usada = NULL;
    if (generar_reporte_categoria(d, es_donantes, mes_sel, d->ruta_fija) == 0) {
        ruta_usada = d->ruta_fija;
    } else if (generar_reporte_categoria(d, es_donantes, mes_sel, d->ruta_relativa) == 0) {
"""
G_N2 = r"""    char mes_sel[8] = "";
    gboolean es_donantes = (d->generador == reporte_generar_donantes);
    int tipo_mes = (d->generador == reporte_generar_vacunas)    ? REPORTE_VACUNAS :
                   (d->generador == reporte_generar_adopciones) ? REPORTE_ADOPCIONES :
                   (d->generador == reporte_generar_alertas)    ? REPORTE_ALERTAS : 0;
    if (es_donantes && !pedir_mes_donantes(GTK_WINDOW(ctx->ventana), mes_sel, sizeof(mes_sel)))
        return;
    if (tipo_mes && !pedir_mes_reporte(GTK_WINDOW(ctx->ventana), tipo_mes, d->nombre_tipo,
                                       mes_sel, sizeof(mes_sel)))
        return;
    char tipo_txt[96];
    snprintf(tipo_txt, sizeof(tipo_txt), "%s", d->nombre_tipo);
    if ((es_donantes || tipo_mes) && mes_sel[0]) {
        char legible[40];
        reporte_mes_legible(mes_sel, legible, (int)sizeof(legible));
        snprintf(tipo_txt, sizeof(tipo_txt), "%s (%s)", d->nombre_tipo, legible);
    }

    const char *ruta_usada = NULL;
    if (generar_reporte_categoria(d, es_donantes, tipo_mes, mes_sel, d->ruta_fija) == 0) {
        ruta_usada = d->ruta_fija;
    } else if (generar_reporte_categoria(d, es_donantes, tipo_mes, mes_sel, d->ruta_relativa) == 0) {
"""

CAMBIOS = {
    DB_H: [(H_VIEJO, H_NUEVO, "declaraciones db.h")],
    DB_C: [(C_VIEJO, C_NUEVO, "funciones nuevas en db.c")],
    GTK_C: [
        (G_A1, G_N1, "ayudante de generacion por categoria"),
        (G_A2, G_N2, "manejador de reportes por categoria"),
    ],
}


def main():
    contenidos = {}
    for ruta in CAMBIOS:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if MARCA in contenidos[DB_H]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)
    if "reporte_generar_donantes_mes" not in contenidos[DB_H]:
        print("ERROR: aplica primero parche-reporte-donantes-mes.py.")
        sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_reportes_mes")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_reportes_mes)")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
