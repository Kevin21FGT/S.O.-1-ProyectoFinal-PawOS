#!/usr/bin/env python3
"""
parche-reporte-donantes-mes.py

Reportes -> boton "Donantes": antes de generar pregunta POR QUE MES.
  - Lista los meses que tienen donaciones (el mas reciente primero), con
    nombre ("Octubre 2026"), y una opcion "Todos los meses".
  - Un mes: solo las donaciones de ese mes, con su total.
  - Todos los meses: agrupado POR MES, cada mes con su subtotal y al final el
    total general (ya no queda todo mezclado).
  - El nombre del mes queda en el titulo del reporte y en el historial
    ("Donantes (Octubre 2026)").

No se toca reporte_generar_donantes() (el reporte general sigue igual); se
agregan funciones nuevas en db.c/db.h y el dialogo en main_gtk.c.

Uso (parado en la raiz del repo):
    python3 parche-reporte-donantes-mes.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
MARCA = "reporte_generar_donantes_mes"

# ------------------------------------------------------------------ db.h
H_VIEJO = "int reporte_generar_donantes(const char *ruta_salida);"
H_NUEVO = """int reporte_generar_donantes(const char *ruta_salida);
/* mes = "AAAA-MM" para un solo mes; NULL o "" = todos, agrupado por mes. */
int reporte_generar_donantes_mes(const char *ruta_salida, const char *mes);
/* "2026-10" -> "Octubre 2026" */
void reporte_mes_legible(const char *ym, char *out, int n);"""

# ------------------------------------------------------------------ db.c
C_VIEJO = "int reporte_generar_alertas(const char *ruta_salida) {"
C_NUEVO = r"""void reporte_mes_legible(const char *ym, char *out, int n) {
    static const char *meses[12] = {
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    };
    int anio = 0, mes = 0;
    if (ym && sscanf(ym, "%d-%d", &anio, &mes) == 2 && mes >= 1 && mes <= 12)
        snprintf(out, (size_t)n, "%s %d", meses[mes - 1], anio);
    else
        snprintf(out, (size_t)n, "%s", ym ? ym : "");
}

static int cmp_donante_fecha(const void *a, const void *b) {
    const Donante *x = a, *y = b;
    int c = strcmp(x->fecha, y->fecha);
    return c ? c : (x->id - y->id);
}

int reporte_generar_donantes_mes(const char *ruta_salida, const char *mes) {
    FILE *f = fopen(ruta_salida, "w");
    if (!f) return -1;

    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    char fecha[32];
    strftime(fecha, sizeof(fecha), "%Y-%m-%d %H:%M:%S", &tmv);

    gboolean_dummy_placeholder
    return 0;
}

int reporte_generar_alertas(const char *ruta_salida) {"""

C_CUERPO = r"""    int un_mes = (mes && mes[0]);
    char legible[40];
    if (un_mes) reporte_mes_legible(mes, legible, (int)sizeof(legible));

    fprintf(f, "===== Reporte de Donantes - PawOS =====\n");
    fprintf(f, "Periodo: %s\n", un_mes ? legible : "Todos los meses (agrupado por mes)");
    fprintf(f, "Generado: %s\n\n", fecha);

    Donante *d = NULL; int nd = 0;
    if (donante_listar(&d, &nd) != 0) { d = NULL; nd = 0; }
    if (nd > 1) qsort(d, (size_t)nd, sizeof(Donante), cmp_donante_fecha);

    char mes_actual[8] = "";
    int cant_mes = 0, cant_total = 0;
    double suma_mes = 0, suma_total = 0;
    int hay_mes_abierto = 0;

    for (int i = 0; i < nd; i++) {
        char ym[8] = "";
        if (strlen(d[i].fecha) >= 7) { memcpy(ym, d[i].fecha, 7); ym[7] = '\0'; }
        if (un_mes && strcmp(ym, mes) != 0) continue;

        if (!un_mes && strcmp(ym, mes_actual) != 0) {
            if (hay_mes_abierto)
                fprintf(f, "  Subtotal: %d donacion(es) - Q%.2f\n\n", cant_mes, suma_mes);
            char etiqueta[40];
            reporte_mes_legible(ym, etiqueta, (int)sizeof(etiqueta));
            fprintf(f, "== %s ==\n", etiqueta);
            snprintf(mes_actual, sizeof(mes_actual), "%s", ym);
            cant_mes = 0; suma_mes = 0; hay_mes_abierto = 1;
        }

        fprintf(f, "  %s (contacto: %s) - Q%.2f - fecha: %s\n",
                d[i].nombre, d[i].contacto, d[i].monto, d[i].fecha);
        cant_mes++; suma_mes += d[i].monto;
        cant_total++; suma_total += d[i].monto;
    }
    if (hay_mes_abierto)
        fprintf(f, "  Subtotal: %d donacion(es) - Q%.2f\n\n", cant_mes, suma_mes);

    if (cant_total == 0)
        fprintf(f, "No hay donaciones registradas en este periodo.\n");
    else
        fprintf(f, "%s: %d donacion(es) - Q%.2f\n",
                un_mes ? "TOTAL DEL MES" : "TOTAL GENERAL", cant_total, suma_total);

    free(d);
    fclose(f);"""

C_NUEVO = C_NUEVO.replace("    gboolean_dummy_placeholder\n", C_CUERPO + "\n")

# ------------------------------------------------------------------ main_gtk.c
G_A1 = "static void on_generar_reporte_categoria_clicked(GtkButton *boton, gpointer datos) {"
G_N1 = r"""/* Pregunta de que mes es el reporte de donantes. out = "AAAA-MM" o "" (todos).
 * Devuelve FALSE si se cancela. */
static gboolean pedir_mes_donantes(GtkWindow *padre, char *out, size_t n_out) {
    Donante *ds = NULL; int nd = 0;
    char meses[120][8];
    int nm = 0;
    if (donante_listar(&ds, &nd) == 0) {
        for (int i = 0; i < nd && nm < 120; i++) {
            if (strlen(ds[i].fecha) < 7) continue;
            char ym[8];
            memcpy(ym, ds[i].fecha, 7); ym[7] = '\0';
            int ya = 0;
            for (int k = 0; k < nm; k++) if (strcmp(meses[k], ym) == 0) { ya = 1; break; }
            if (!ya) { memcpy(meses[nm], ym, 8); nm++; }
        }
    }
    free(ds);
    /* mas reciente primero */
    for (int a = 0; a < nm; a++)
        for (int b = a + 1; b < nm; b++)
            if (strcmp(meses[a], meses[b]) < 0) {
                char tmp[8]; memcpy(tmp, meses[a], 8);
                memcpy(meses[a], meses[b], 8); memcpy(meses[b], tmp, 8);
            }

    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Reporte de donantes", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Generar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
    GtkWidget *lbl = gtk_label_new("De que mes quieres el reporte de donantes?");
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

static int generar_reporte_categoria(DatosReporteCategoria *d, gboolean es_donantes,
                                     const char *mes, const char *ruta) {
    return es_donantes ? reporte_generar_donantes_mes(ruta, mes) : d->generador(ruta);
}

static void on_generar_reporte_categoria_clicked(GtkButton *boton, gpointer datos) {"""

G_A2 = r"""    const char *ruta_usada = NULL;
    if (d->generador(d->ruta_fija) == 0) {
        ruta_usada = d->ruta_fija;
    } else if (d->generador(d->ruta_relativa) == 0) {
        ruta_usada = d->ruta_relativa;
    }

    if (ruta_usada == NULL) {
        char msg[200];"""
G_N2 = r"""    char mes_sel[8] = "";
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
        ruta_usada = d->ruta_relativa;
    }

    if (ruta_usada == NULL) {
        char msg[200];"""

G_A3 = 'snprintf(estado_txt, sizeof(estado_txt), "Reporte de %s generado en: %s", d->nombre_tipo, ruta_usada);'
G_N3 = 'snprintf(estado_txt, sizeof(estado_txt), "Reporte de %s generado en: %s", tipo_txt, ruta_usada);'

G_A4 = "    agregar_entrada_historial(ctx, d->nombre_tipo);"
G_N4 = "    agregar_entrada_historial(ctx, tipo_txt);"

CAMBIOS = {
    DB_H: [(H_VIEJO, H_NUEVO, "declaraciones db.h")],
    DB_C: [(C_VIEJO, C_NUEVO, "funciones nuevas en db.c")],
    GTK_C: [
        (G_A1, G_N1, "inicio del manejador de reportes por categoria"),
        (G_A2, G_N2, "generacion del reporte por categoria"),
        (G_A3, G_N3, "texto de estado"),
        (G_A4, G_N4, "entrada del historial"),
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

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_donantes_mes")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_donantes_mes)")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
