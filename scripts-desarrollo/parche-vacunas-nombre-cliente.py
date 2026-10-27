#!/usr/bin/env python3
"""
parche-vacunas-nombre-cliente.py   (aplicar DESPUES de parche-vacunas-nombre-mascota.py)

Refugio GUI -> Agenda de Vacunas: agrega la columna "Cliente" con el
nombre del Cliente a notificar (el que recibe el correo/WhatsApp).
Si la vacuna no tiene Cliente asignado muestra "-".

Uso (parado en la raiz del repo):
    python3 parche-vacunas-nombre-cliente.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "COL_V_CLIENTE_NOM"

CAMBIOS = [
    ("""    COL_V_MASCOTA_NOM,
    COL_V_NOMBRE,""",
     """    COL_V_MASCOTA_NOM,
    COL_V_CLIENTE_NOM,
    COL_V_NOMBRE,""",
     "enum de columnas"),
    ("""static void cargar_vacunas(ContextoVacunas *ctx) {""",
     """static const char *nombre_cliente_de_vacuna(const Cliente *cs, int n, int id) {
    if (id <= 0) return "-";
    for (int i = 0; i < n; i++)
        if (cs[i].id == id) return cs[i].nombre;
    return "(cliente eliminado)";
}

static void cargar_vacunas(ContextoVacunas *ctx) {""",
     "funcion auxiliar"),
    ("""    if (mascota_listar(&ms_nombres, &n_ms_nombres) != 0) { ms_nombres = NULL; n_ms_nombres = 0; }
""",
     """    if (mascota_listar(&ms_nombres, &n_ms_nombres) != 0) { ms_nombres = NULL; n_ms_nombres = 0; }
    Cliente *cl_nombres = NULL;
    int n_cl_nombres = 0;
    if (cliente_listar(&cl_nombres, &n_cl_nombres) != 0) { cl_nombres = NULL; n_cl_nombres = 0; }
""",
     "lectura de clientes"),
    ("""            COL_V_MASCOTA_NOM, nombre_mascota_de_vacuna(ms_nombres, n_ms_nombres, vs[i].mascota_id),
""",
     """            COL_V_MASCOTA_NOM, nombre_mascota_de_vacuna(ms_nombres, n_ms_nombres, vs[i].mascota_id),
            COL_V_CLIENTE_NOM, nombre_cliente_de_vacuna(cl_nombres, n_cl_nombres, vs[i].cliente_id),
""",
     "fila de vacuna"),
    ("""    free(ms_nombres);
}""",
     """    free(ms_nombres);
    free(cl_nombres);
}""",
     "liberar clientes"),
    ("""G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_VACUNAS] = {"ID", "ID Mascota", "Mascota", "Vacuna", "Aplicada", "Proxima", "Observaciones"};""",
     """G_TYPE_INT, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_VACUNAS] = {"ID", "ID Mascota", "Mascota", "Cliente", "Vacuna", "Aplicada", "Proxima", "Observaciones"};""",
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

    if "COL_V_MASCOTA_NOM" not in contenido:
        print("ERROR: aplica primero parche-vacunas-nombre-mascota.py.")
        sys.exit(1)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_vacunas_cliente")
    print(f"Backup: {ARCHIVO}.bak_vacunas_cliente")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
