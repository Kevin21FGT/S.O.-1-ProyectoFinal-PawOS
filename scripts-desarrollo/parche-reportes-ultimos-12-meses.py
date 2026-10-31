#!/usr/bin/env python3
"""
parche-reportes-ultimos-12-meses.py   (despues de parche-reportes-por-mes.py)

El selector de mes de los reportes (Donantes, Vacunas, Adopciones, Alertas)
ahora siempre incluye los ULTIMOS 12 MESES (mes y anio), ademas de los meses
que tengan registros. Asi se puede sacar el reporte de, por ejemplo, Julio
aunque ese mes este vacio. El primero de la lista es el mes actual.

Uso (parado en la raiz del repo):
    python3 parche-reportes-ultimos-12-meses.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
MARCA = "reporte_completar_ultimos_meses"

H_VIEJO = "int reporte_listar_meses(int tipo, char (*meses)[8], int max);"
H_NUEVO = """int reporte_listar_meses(int tipo, char (*meses)[8], int max);
/* Agrega los ultimos 12 meses (hasta hoy) a la lista y la deja del mas reciente al mas antiguo. */
int reporte_completar_ultimos_meses(char (*meses)[8], int nm, int max);"""

C_VIEJO = "int reporte_listar_meses(int tipo, char (*meses)[8], int max) {"
C_NUEVO = r"""int reporte_completar_ultimos_meses(char (*meses)[8], int nm, int max) {
    time_t t = time(NULL);
    struct tm tmv; localtime_r(&t, &tmv);
    int anio = tmv.tm_year + 1900, mes = tmv.tm_mon + 1;
    for (int k = 0; k < 12; k++) {
        char ym[16];
        snprintf(ym, sizeof(ym), "%04d-%02d", anio, mes);
        int ya = 0;
        for (int i = 0; i < nm; i++) if (strcmp(meses[i], ym) == 0) { ya = 1; break; }
        if (!ya && nm < max) { memcpy(meses[nm], ym, 8); nm++; }
        if (--mes == 0) { mes = 12; anio--; }
    }
    for (int a = 0; a < nm; a++)
        for (int b = a + 1; b < nm; b++)
            if (strcmp(meses[a], meses[b]) < 0) {
                char tmp[8]; memcpy(tmp, meses[a], 8);
                memcpy(meses[a], meses[b], 8); memcpy(meses[b], tmp, 8);
            }
    return nm;
}

int reporte_listar_meses(int tipo, char (*meses)[8], int max) {"""

G_A1 = """    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Reporte de donantes", padre, GTK_DIALOG_MODAL,"""
G_N1 = """    nm = reporte_completar_ultimos_meses(meses, nm, 120);

    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Reporte de donantes", padre, GTK_DIALOG_MODAL,"""

G_A2 = "    int nm = reporte_listar_meses(tipo, meses, 120);"
G_N2 = """    int nm = reporte_listar_meses(tipo, meses, 120);
    nm = reporte_completar_ultimos_meses(meses, nm, 120);"""

CAMBIOS = {
    DB_H: [(H_VIEJO, H_NUEVO, "declaracion en db.h")],
    DB_C: [(C_VIEJO, C_NUEVO, "funcion nueva en db.c")],
    GTK_C: [
        (G_A1, G_N1, "selector de mes de Donantes"),
        (G_A2, G_N2, "selector de mes de Vacunas/Adopciones/Alertas"),
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
    if "reporte_listar_meses" not in contenidos[DB_H]:
        print("ERROR: aplica primero parche-reportes-por-mes.py.")
        sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_12_meses")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_12_meses)")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
