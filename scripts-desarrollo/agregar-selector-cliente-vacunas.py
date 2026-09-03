#!/usr/bin/env python3
"""
agregar-selector-cliente-vacunas.py

Segundo paso de la funcion de recordatorios: agrega un selector
"Cliente a notificar (opcional)" al formulario de "Registrar vacuna"
en Agenda de Vacunas, y guarda ese vinculo en la columna
vacunas.cliente_id (agregada por agregar-telefono-cliente.py).

No cambia nada de lo que ya funciona -- el campo es opcional
("(Ninguno)" por defecto), asi que registrar una vacuna sin elegir
Cliente sigue funcionando exactamente igual que antes.

Requisito: correr DESPUES de agregar-telefono-cliente.py.

Toca:
  - src/db/db.h: struct Vacuna gana "cliente_id"; se agrega la
    declaracion de cliente_listar().
  - src/db/db.c: vacuna_agregar() guarda cliente_id; se agrega
    cliente_listar() (mismo patron que usuario_listar()).
  - src/main_gtk.c: on_registrar_vacuna_clicked() gana el selector
    y lo guarda en v.cliente_id.

Uso: parado en la raiz del repo:
    python3 agregar-selector-cliente-vacunas.py
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"

# ---------------------------------------------------------------
# db.h
# ---------------------------------------------------------------
ANCLA_H_VACUNA = """typedef struct {
    int  id;
    int  mascota_id;
    char nombre_vacuna[64];
    char fecha_aplicacion[16];
    char fecha_proxima[16];
    char observaciones[128]; /* notas libres sobre esta vacuna, opcional */
} Vacuna;"""
NUEVO_H_VACUNA = """typedef struct {
    int  id;
    int  mascota_id;
    char nombre_vacuna[64];
    char fecha_aplicacion[16];
    char fecha_proxima[16];
    char observaciones[128]; /* notas libres sobre esta vacuna, opcional */
    int  cliente_id; /* 0 = sin Cliente asignado para notificar */
} Vacuna;"""

ANCLA_H_DECL = """int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
const char *cliente_rol_nombre(RolCliente rol);"""
NUEVO_H_DECL = """int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
const char *cliente_rol_nombre(RolCliente rol);
int  cliente_listar(Cliente **out, int *n);"""

# ---------------------------------------------------------------
# db.c
# ---------------------------------------------------------------
ANCLA_C_AGREGAR = """int vacuna_agregar(const Vacuna *v) {
    const char *sql =
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima, observaciones) "
        "VALUES (?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, v->mascota_id);
    sqlite3_bind_text(st, 2, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 5, v->observaciones, -1, SQLITE_STATIC);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""
NUEVO_C_AGREGAR = """int vacuna_agregar(const Vacuna *v) {
    const char *sql =
        "INSERT INTO vacunas (mascota_id, nombre_vacuna, fecha_aplicacion, fecha_proxima, observaciones, cliente_id) "
        "VALUES (?,?,?,?,?,?);";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, v->mascota_id);
    sqlite3_bind_text(st, 2, v->nombre_vacuna, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 3, v->fecha_aplicacion, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 4, v->fecha_proxima, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 5, v->observaciones, -1, SQLITE_STATIC);
    if (v->cliente_id > 0) {
        sqlite3_bind_int(st, 6, v->cliente_id);
    } else {
        sqlite3_bind_null(st, 6);
    }
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

ANCLA_C_LISTAR = """    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Clientes (publico externo) ---------------- */

"""
NUEVO_C_LISTAR = """    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

/* ---------------- Clientes (publico externo) ---------------- */

/* Lista los Clientes registrados (id, correo, nombre, telefono, rol),
 * usado para llenar el selector "Cliente a notificar" al registrar
 * una vacuna/cita en Agenda de Vacunas. */
int cliente_listar(Cliente **out, int *n) {
    const char *sql = "SELECT id, correo, nombre, telefono, rol FROM clientes ORDER BY nombre;";
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) return -1;
    int cap = 8, cnt = 0;
    Cliente *arr = malloc(sizeof(Cliente) * cap);
    while (sqlite3_step(st) == SQLITE_ROW) {
        if (cnt == cap) { cap *= 2; arr = realloc(arr, sizeof(Cliente) * cap); }
        Cliente *c = &arr[cnt++];
        c->id = sqlite3_column_int(st, 0);
        snprintf(c->correo, sizeof(c->correo), "%s", (const char *)sqlite3_column_text(st, 1));
        snprintf(c->nombre, sizeof(c->nombre), "%s", (const char *)sqlite3_column_text(st, 2));
        const unsigned char *tel = sqlite3_column_text(st, 3);
        snprintf(c->telefono, sizeof(c->telefono), "%s", tel ? (const char *)tel : "");
        c->rol = (RolCliente)sqlite3_column_int(st, 4);
    }
    sqlite3_finalize(st);
    *out = arr;
    *n = cnt;
    return 0;
}

"""

# ---------------------------------------------------------------
# main_gtk.c
# ---------------------------------------------------------------
ANCLA_GTK_CAMPOS = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_aplic  = gtk_entry_new();
    GtkWidget *e_prox   = gtk_entry_new();
    GtkWidget *e_obs    = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_aplic), "AAAA-MM-DD");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_prox), "AAAA-MM-DD (opcional)");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_obs), "Opcional");

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre de la vacuna:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Fecha de aplicacion:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_aplic, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Proxima dosis:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_prox, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Observaciones:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_obs, 1, 3, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);"""
NUEVO_GTK_CAMPOS = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_aplic  = gtk_entry_new();
    GtkWidget *e_prox   = gtk_entry_new();
    GtkWidget *e_obs    = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_aplic), "AAAA-MM-DD");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_prox), "AAAA-MM-DD (opcional)");
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_obs), "Opcional");

    GtkWidget *e_cliente = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_cliente), "0", "(Ninguno)");
    Cliente *lista_clientes_vac = NULL;
    int n_clientes_vac = 0;
    cliente_listar(&lista_clientes_vac, &n_clientes_vac);
    for (int i = 0; i < n_clientes_vac; i++) {
        char id_cliente_txt[16];
        snprintf(id_cliente_txt, sizeof(id_cliente_txt), "%d", lista_clientes_vac[i].id);
        gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_cliente), id_cliente_txt, lista_clientes_vac[i].nombre);
    }
    gtk_combo_box_set_active(GTK_COMBO_BOX(e_cliente), 0);

    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Nombre de la vacuna:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Fecha de aplicacion:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_aplic, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Proxima dosis:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_prox, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Observaciones:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_obs, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Cliente a notificar (opcional):"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), e_cliente, 1, 4, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);"""

ANCLA_GTK_GUARDAR = """
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));

        if (vacuna_agregar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna registrada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la vacuna.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}"""
NUEVO_GTK_GUARDAR = """
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));
        const gchar *cliente_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_cliente));
        v.cliente_id = cliente_id_texto ? atoi(cliente_id_texto) : 0;

        if (vacuna_agregar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna registrada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la vacuna.", TRUE);
        }
    }
    free(lista_clientes_vac);
    gtk_widget_destroy(dialogo);
}"""


def main():
    archivos = [
        (ARCHIVO_DB_H, [
            (ANCLA_H_VACUNA, NUEVO_H_VACUNA, "struct Vacuna"),
            (ANCLA_H_DECL, NUEVO_H_DECL, "declaracion cliente_listar"),
        ]),
        (ARCHIVO_DB_C, [
            (ANCLA_C_AGREGAR, NUEVO_C_AGREGAR, "vacuna_agregar"),
            (ANCLA_C_LISTAR, NUEVO_C_LISTAR, "cliente_listar"),
        ]),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_CAMPOS, NUEVO_GTK_CAMPOS, "campos del formulario de vacuna"),
            (ANCLA_GTK_GUARDAR, NUEVO_GTK_GUARDAR, "manejo del boton Guardar"),
        ]),
    ]

    contenidos = {}
    for ruta, pares in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        for ancla, _nuevo, nombre in pares:
            if contenido.count(ancla) != 1:
                print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
                print("       Puede que agregar-telefono-cliente.py no se haya aplicado todavia,")
                print("       o que el archivo ya haya sido modificado. No se cambio nada.")
                sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, pares in archivos:
        contenido = contenidos[ruta]
        for ancla, nuevo, _nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak2")
        print(f"Backup creado: {ruta}.bak2")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Ahora compila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")


if __name__ == "__main__":
    main()
