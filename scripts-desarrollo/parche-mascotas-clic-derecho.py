#!/usr/bin/env python3
"""
parche-mascotas-clic-derecho.py

Refugio GUI -> Gestion de Mascotas: clic derecho sobre una mascota con
  Editar datos (nombre, especie, raza, edad), Foto, Cambiar estado, Eliminar.
Los botones de abajo se mantienen. Voluntario solo puede ver la Foto.

Agrega mascota_actualizar_datos() a db.c/db.h (UPDATE en SQL Server).

Uso (parado en la raiz del repo):
    python3 parche-mascotas-clic-derecho.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"
MARCA = "static gboolean on_mascotas_clic("

DB_FUNC = r"""int mascota_actualizar_datos(int id, const char *nombre, const char *especie,
                              const char *raza, int edad) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;

    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)
        "UPDATE mascotas SET nombre=?, especie=?, raza=?, edad=? WHERE id=?;", SQL_NTS);

    char b_nombre[128], b_especie[128], b_raza[128];
    snprintf(b_nombre, sizeof(b_nombre), "%s", nombre ? nombre : "");
    snprintf(b_especie, sizeof(b_especie), "%s", especie ? especie : "");
    snprintf(b_raza, sizeof(b_raza), "%s", raza ? raza : "");
    SQLINTEGER edad_val = edad, id_val = id;
    SQLLEN l1 = SQL_NTS, l2 = SQL_NTS, l3 = SQL_NTS;

    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 127, 0, b_nombre, 0, &l1);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 127, 0, b_especie, 0, &l2);
    SQLBindParameter(hstmt, 3, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, 127, 0, b_raza, 0, &l3);
    SQLBindParameter(hstmt, 4, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &edad_val, 0, NULL);
    SQLBindParameter(hstmt, 5, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);

    SQLRETURN ret = SQLExecute(hstmt);
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return SQL_SUCCEEDED(ret) ? 0 : -1;
}

int mascota_eliminar(int id) {"""

GTK_FUNC = r"""/* ---- Clic derecho en Gestion de Mascotas ---- */
static void editar_datos_mascota(ContextoMascotas *ctx) {
    int id;
    if (!obtener_id_seleccionado(ctx->treeview, COL_M_ID, &id)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una mascota de la lista.", TRUE);
        return;
    }
    Mascota m;
    memset(&m, 0, sizeof(m));
    if (mascota_buscar_por_id(id, &m) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer esa mascota.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar datos de la mascota", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 12);

    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_especie = gtk_entry_new();
    GtkWidget *e_raza = gtk_entry_new();
    GtkWidget *e_edad = gtk_spin_button_new_with_range(0, 99, 1);
    gtk_entry_set_text(GTK_ENTRY(e_nombre), m.nombre);
    gtk_entry_set_text(GTK_ENTRY(e_especie), m.especie);
    gtk_entry_set_text(GTK_ENTRY(e_raza), m.raza);
    gtk_spin_button_set_value(GTK_SPIN_BUTTON(e_edad), m.edad);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Especie:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_especie, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Raza:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_raza, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Edad:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_edad, 1, 3, 1, 1);
    gtk_container_add(GTK_CONTAINER(area), grid);
    gtk_widget_show_all(dialogo);

    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;
        const char *nom = gtk_entry_get_text(GTK_ENTRY(e_nombre));
        const char *esp = gtk_entry_get_text(GTK_ENTRY(e_especie));
        const char *raz = gtk_entry_get_text(GTK_ENTRY(e_raza));
        int edad = gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(e_edad));
        if (nom[0] == '\0' || esp[0] == '\0') {
            mostrar_mensaje(GTK_WINDOW(dialogo), "El nombre y la especie son obligatorios.", TRUE);
            continue;
        }
        if (mascota_actualizar_datos(id, nom, esp, raz, edad) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo actualizar la mascota.", TRUE);
            continue;
        }
        cargar_mascotas(ctx);
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Mascota actualizada.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

static void on_mascotas_menu_editar(GtkMenuItem *item, gpointer datos) {
    (void)item;
    editar_datos_mascota((ContextoMascotas *)datos);
}
static void on_mascotas_menu_foto(GtkMenuItem *item, gpointer datos) {
    (void)item;
    on_foto_mascota_clicked(NULL, datos);
}
static void on_mascotas_menu_estado(GtkMenuItem *item, gpointer datos) {
    (void)item;
    on_cambiar_estado_clicked(NULL, datos);
}
static void on_mascotas_menu_eliminar(GtkMenuItem *item, gpointer datos) {
    (void)item;
    on_eliminar_clicked(NULL, datos);
}

static gboolean on_mascotas_clic(GtkWidget *vista, GdkEventButton *ev, gpointer datos) {
    ContextoMascotas *ctx = (ContextoMascotas *)datos;
    if (ev->type != GDK_BUTTON_PRESS || ev->button != 3) return FALSE;
    GtkTreePath *ruta = NULL;
    if (!gtk_tree_view_get_path_at_pos(GTK_TREE_VIEW(vista), (gint)ev->x, (gint)ev->y,
                                       &ruta, NULL, NULL, NULL))
        return FALSE;
    gtk_tree_view_set_cursor(GTK_TREE_VIEW(vista), ruta, NULL, FALSE);
    gtk_tree_path_free(ruta);

    GtkWidget *menu = gtk_menu_new();
    GtkWidget *it_editar = gtk_menu_item_new_with_label("Editar datos");
    GtkWidget *it_foto = gtk_menu_item_new_with_label("Foto");
    GtkWidget *it_estado = gtk_menu_item_new_with_label("Cambiar estado");
    GtkWidget *it_elim = gtk_menu_item_new_with_label("Eliminar");
    if (ctx->rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(it_editar, FALSE);
        gtk_widget_set_sensitive(it_estado, FALSE);
        gtk_widget_set_sensitive(it_elim, FALSE);
    }
    g_signal_connect(it_editar, "activate", G_CALLBACK(on_mascotas_menu_editar), ctx);
    g_signal_connect(it_foto, "activate", G_CALLBACK(on_mascotas_menu_foto), ctx);
    g_signal_connect(it_estado, "activate", G_CALLBACK(on_mascotas_menu_estado), ctx);
    g_signal_connect(it_elim, "activate", G_CALLBACK(on_mascotas_menu_eliminar), ctx);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_editar);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_foto);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_estado);
    gtk_menu_shell_append(GTK_MENU_SHELL(menu), it_elim);
    gtk_widget_show_all(menu);
    gtk_menu_popup_at_pointer(GTK_MENU(menu), (GdkEvent *)ev);
    return TRUE;
}

static void on_refrescar_mascotas_clicked(GtkButton *boton, gpointer datos) {"""

CAMBIOS = {
    DB_H: [
        ("int  mascota_buscar_por_id(int id, Mascota *out);",
         "int  mascota_buscar_por_id(int id, Mascota *out);\n"
         "int  mascota_actualizar_datos(int id, const char *nombre, const char *especie,\n"
         "                              const char *raza, int edad);",
         "declaracion en db.h"),
    ],
    DB_C: [
        ("int mascota_eliminar(int id) {", DB_FUNC, "mascota_eliminar en db.c"),
    ],
    GTK_C: [
        ("static void on_refrescar_mascotas_clicked(GtkButton *boton, gpointer datos) {",
         GTK_FUNC, "on_refrescar_mascotas_clicked"),
        ("""    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    cargar_mascotas(ctx);""",
         """    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);
    g_signal_connect(ctx->treeview, "button-press-event", G_CALLBACK(on_mascotas_clic), ctx);

    cargar_mascotas(ctx);""",
         "conexion en el panel de mascotas"),
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

    if MARCA in contenidos[GTK_C]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_mascotas_clic")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_mascotas_clic)")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
