#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-validar-fecha-vacunas.py

Agrega validacion de formato de fecha (AAAA-MM-DD, fecha real) al
dialogo "Registrar vacuna" de PawOS Refugio GUI (main_gtk.c).

Por que: vacuna_pendientes() en db.c compara fechas como texto, lo
cual solo funciona bien si TODAS las fechas guardadas usan el mismo
formato AAAA-MM-DD. Sin esta validacion, el campo de texto libre
aceptaba cualquier cosa (incluso fechas invalidas como "31-09-2026"),
rompiendo el filtro de "pendientes/vencidas".

No cambia nada de la logica de guardado ni de notificaciones: solo
agrega una vuelta de validacion antes de aceptar los datos del
dialogo. Si la fecha no es valida, se muestra un mensaje y se vuelve
a mostrar el mismo dialogo (los datos ya escritos no se pierden).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-validar-fecha-vacunas.py
"""
import shutil
import sys
from pathlib import Path

MAIN_GTK_C = Path("src/main_gtk.c")

ANCLA_HELPER = "static void on_registrar_vacuna_clicked(GtkButton *boton, gpointer datos) {"

NUEVO_HELPER = """/* Valida que una fecha tenga el formato estricto AAAA-MM-DD y sea una
 * fecha real (dia valido para ese mes/anio, incluyendo anios
 * bisiestos). Necesario porque vacuna_pendientes() en db.c compara
 * fechas como texto, y eso solo funciona bien si todas las fechas
 * guardadas usan este mismo formato. */
static gboolean fecha_valida(const char *fecha) {
    if (!fecha || strlen(fecha) != 10) return FALSE;
    if (fecha[4] != '-' || fecha[7] != '-') return FALSE;
    int anio, mes, dia;
    if (sscanf(fecha, "%4d-%2d-%2d", &anio, &mes, &dia) != 3) return FALSE;
    if (mes < 1 || mes > 12) return FALSE;
    if (dia < 1 || dia > 31) return FALSE;
    static const int dias_por_mes[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    int max_dia = dias_por_mes[mes - 1];
    if (mes == 2) {
        gboolean bisiesto = (anio % 4 == 0 && (anio % 100 != 0 || anio % 400 == 0));
        if (bisiesto) max_dia = 29;
    }
    return dia <= max_dia;
}

static void on_registrar_vacuna_clicked(GtkButton *boton, gpointer datos) {"""

ANCLA_DIALOGO = """    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    mostrar_con_fundido(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));"""

NUEVO_DIALOGO = """    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    mostrar_con_fundido(dialogo);

    gboolean datos_vacuna_ok = FALSE;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;
        const char *fapl_txt = gtk_entry_get_text(GTK_ENTRY(e_aplic));
        const char *fprox_txt = gtk_entry_get_text(GTK_ENTRY(e_prox));
        if (!fecha_valida(fapl_txt)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La fecha de aplicacion debe tener el formato AAAA-MM-DD y ser una fecha valida (ej: 2026-10-16).",
                TRUE);
            continue;
        }
        if (fprox_txt[0] != '\\0' && !fecha_valida(fprox_txt)) {
            mostrar_mensaje(GTK_WINDOW(dialogo),
                "La proxima dosis debe tener el formato AAAA-MM-DD, o dejarse vacia si no aplica.",
                TRUE);
            continue;
        }
        datos_vacuna_ok = TRUE;
        break;
    }

    if (datos_vacuna_ok) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));"""

REEMPLAZOS = [
    ("helper fecha_valida", ANCLA_HELPER, NUEVO_HELPER),
    ("dialogo registrar vacuna", ANCLA_DIALOGO, NUEVO_DIALOGO),
]


def main():
    if not MAIN_GTK_C.exists():
        print(f"ERROR: no se encontro {MAIN_GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = MAIN_GTK_C.read_text(encoding="utf-8")

    for nombre, ancla, _ in REEMPLAZOS:
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en src/main_gtk.c.")
            print("       (puede que ya este parchado, o el codigo cambio)")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar automaticamente.")
            sys.exit(1)

    backup = MAIN_GTK_C.with_suffix(".c.bak_validar_fecha")
    shutil.copy(MAIN_GTK_C, backup)

    for nombre, ancla, nuevo in REEMPLAZOS:
        contenido = contenido.replace(ancla, nuevo, 1)

    MAIN_GTK_C.write_text(contenido, encoding="utf-8")

    print(f"  {MAIN_GTK_C}: 'Registrar vacuna' ahora valida el formato de fecha. Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  make gui")
    print("  Corrige la vacuna de prueba con fechas invalidas desde PawOS Vacunas GUI")
    print("  (seleccionala, Editar, escribe fechas AAAA-MM-DD validas, Guardar).")


if __name__ == "__main__":
    main()
