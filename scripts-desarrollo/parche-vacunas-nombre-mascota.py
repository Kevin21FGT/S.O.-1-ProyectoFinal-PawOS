#!/usr/bin/env python3
"""
parche-vacunas-nombre-mascota.py

Refugio GUI -> Agenda de Vacunas: agrega la columna "Mascota" con el
NOMBRE de la mascota, junto a "ID Mascota".

Uso (parado en la raiz del repo):
    python3 parche-vacunas-nombre-mascota.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "COL_V_MASCOTA_NOM"

CAMBIOS = [
    ("""    COL_V_MASCOTA_ID,
    COL_V_NOMBRE,
    COL_V_APLICACION,""",
     """    COL_V_MASCOTA_ID,
    COL_V_MASCOTA_NOM,
    COL_V_NOMBRE,
    COL_V_APLICACION,""",
     "enum de columnas"),
    ("""    Vacuna *vs;
    int n;
    int rc = ctx->solo_pendientes ? vacuna_pendientes(&vs, &n) : vacuna_listar(&vs, &n);
    if (rc != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de vacunas.", TRUE);
        return;
    }
""",
     """    Vacuna *vs;
    int n;
    int rc = ctx->solo_pendientes ? vacuna_pendientes(&vs, &n) : vacuna_listar(&vs, &n);
    if (rc != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de vacunas.", TRUE);
        return;
    }
    Mascota *ms_nombres = NULL;
    int n_ms_nombres = 0;
    if (mascota_listar(&ms_nombres, &n_ms_nombres) != 0) { ms_nombres = NULL; n_ms_nombres = 0; }
""",
     "lectura de vacunas"),
    ("""            COL_V_ID, vs[i].id,
            COL_V_MASCOTA_ID, vs[i].mascota_id,
""",
     """            COL_V_ID, vs[i].id,
            COL_V_MASCOTA_ID, vs[i].mascota_id,
            COL_V_MASCOTA_NOM, nombre_mascota_de_vacuna(ms_nombres, n_ms_nombres, vs[i].mascota_id),
""",
     "fila de vacuna"),
    ("""    free(vs);
}

static void on_ver_todas_vacunas_clicked""",
     """    free(vs);
    free(ms_nombres);
}

static void on_ver_todas_vacunas_clicked""",
     "liberar nombres"),
    ("""static void cargar_vacunas(ContextoVacunas *ctx) {""",
     """static const char *nombre_mascota_de_vacuna(const Mascota *ms, int n, int id) {
    for (int i = 0; i < n; i++)
        if (ms[i].id == id) return ms[i].nombre;
    return "(sin mascota)";
}

static void cargar_vacunas(ContextoVacunas *ctx) {""",
     "funcion auxiliar"),
    ("""        G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_VACUNAS] = {"ID", "ID Mascota", "Vacuna", "Aplicada", "Proxima", "Observaciones"};""",
     """        G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_VACUNAS] = {"ID", "ID Mascota", "Mascota", "Vacuna", "Aplicada", "Proxima", "Observaciones"};""",
     "tabla y encabezados"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_vacunas_nombre")
    print(f"Backup: {ARCHIVO}.bak_vacunas_nombre")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
