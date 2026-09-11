#!/usr/bin/env python3
"""
quitar-rol-registro-agregar-admin-clientes.py

1) Quita el selector "Tu rol en tu organizacion" del registro publico
   de Cliente -- si cualquiera pudiera auto-asignarse el nivel mas
   alto, nadie elegiria uno mas bajo y la jerarquia no serviria de
   nada. Todo Cliente nuevo entra ahora en el nivel base (Jefe).

2) Agrega una pantalla nueva "Administrar Clientes" (solo
   Administrador) para poder subir/bajar el rol de un Cliente despues
   del registro -- mismo patron que "Administrar Colaboradores" y
   "Configurar Notificaciones", pero sin contexto en el heap (no hay
   nada que liberar al cerrar, asi que no hay riesgo del bug de
   g_signal_connect que ya se arreglo antes en Administrar
   Colaboradores).

No cambia nada de lo demas -- login, permisos de Colaborador, etc.
siguen exactamente igual.

Requisito: correr DESPUES de agregar-pantalla-notificaciones.py (usa
el bloque de "Configurar Notificaciones" como ancla para los arreglos
del dashboard).

Uso: parado en la raiz del repo:
    python3 quitar-rol-registro-agregar-admin-clientes.py
"""

import shutil
import sys

ARCHIVO_DB_H = "src/db/db.h"
ARCHIVO_DB_C = "src/db/db.c"
ARCHIVO_GTK = "src/main_gtk.c"

# ---------------------------------------------------------------
# db.h / db.c: cliente_actualizar_rol()
# ---------------------------------------------------------------
ANCLA_H = """int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
const char *cliente_rol_nombre(RolCliente rol);
int  cliente_listar(Cliente **out, int *n);"""
NUEVO_H = """int  cliente_actualizar(int id, const char *nombre, const char *password_nueva);
int  cliente_actualizar_rol(int id, RolCliente nuevo_rol);
const char *cliente_rol_nombre(RolCliente rol);
int  cliente_listar(Cliente **out, int *n);"""

ANCLA_C = """const char *cliente_rol_nombre(RolCliente rol) {
    switch (rol) {
        case ROL_CLIENTE_ADMIN: return "Administrador";
        case ROL_CLIENTE_SUPERVISOR: return "Supervisor";
        default: return "Jefe";
    }
}"""
NUEVO_C = """const char *cliente_rol_nombre(RolCliente rol) {
    switch (rol) {
        case ROL_CLIENTE_ADMIN: return "Administrador";
        case ROL_CLIENTE_SUPERVISOR: return "Supervisor";
        default: return "Jefe";
    }
}
int cliente_actualizar_rol(int id, RolCliente nuevo_rol) {
    sqlite3_stmt *st;
    if (sqlite3_prepare_v2(g_db, "UPDATE clientes SET rol=? WHERE id=?;", -1, &st, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int(st, 1, (int)nuevo_rol);
    sqlite3_bind_int(st, 2, id);
    int rc = sqlite3_step(st);
    sqlite3_finalize(st);
    return rc == SQLITE_DONE ? 0 : -1;
}"""

# ---------------------------------------------------------------
# main_gtk.c: quitar el selector del registro
# ---------------------------------------------------------------
ANCLA_GTK_CAMPOS = """    GtkWidget *e_telefono = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(e_telefono), GTK_INPUT_PURPOSE_PHONE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_telefono), "Ej: 50412345678 (con codigo de pais)");

    GtkWidget *e_rol = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(e_rol), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(e_rol), 0);

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Telefono (WhatsApp):"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_telefono, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Tu rol en tu organizacion:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_rol, 1, 4, 1, 1);"""
NUEVO_GTK_CAMPOS = """    GtkWidget *e_telefono = gtk_entry_new();
    gtk_entry_set_input_purpose(GTK_ENTRY(e_telefono), GTK_INPUT_PURPOSE_PHONE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_telefono), "Ej: 50412345678 (con codigo de pais)");

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_correo, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_password, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Telefono (WhatsApp):"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_telefono, 1, 3, 1, 1);"""

ANCLA_GTK_ACEPTAR = """        const char *telefono = gtk_entry_get_text(GTK_ENTRY(e_telefono));
        const gchar *rol_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_rol));
        RolCliente rol_elegido = rol_id_texto ? (RolCliente)atoi(rol_id_texto) : ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, telefono, rol_elegido) == 0
                && cliente_autenticar(correo, password, cliente_out) == 0) {"""
NUEVO_GTK_ACEPTAR = """        const char *telefono = gtk_entry_get_text(GTK_ENTRY(e_telefono));
        /* Ya no se deja elegir el rol al registrarse: si cualquiera
         * pudiera auto-asignarse el nivel mas alto, nadie elegiria uno
         * mas bajo y la jerarquia no serviria de nada. Todo Cliente
         * nuevo entra en el nivel base; el Administrador del refugio
         * lo puede subir despues desde "Administrar Clientes". */
        RolCliente rol_elegido = ROL_CLIENTE_JEFE;
        if (nombre[0] && correo[0] && password[0]) {
            if (cliente_registrar(correo, password, nombre, telefono, rol_elegido) == 0
                && cliente_autenticar(correo, password, cliente_out) == 0) {"""

# ---------------------------------------------------------------
# main_gtk.c: modulo_permitido + nueva funcion + arreglos del dashboard
# (usa el estado dejado por agregar-pantalla-notificaciones.py)
# ---------------------------------------------------------------
ANCLA_PERMISOS = """static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9 || indice == 10);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9 || indice == 10);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}"""
NUEVO_PERMISOS = """static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9 || indice == 10 || indice == 11);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9 || indice == 10 || indice == 11);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}

/* Cambia el rol (Jefe/Supervisor/Administrador) de un Cliente ya
 * registrado -- necesario porque el registro publico ya no deja
 * elegirlo (ver mostrar_registro_cliente). Solo Administrador. */
static void on_cambiar_rol_cliente_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkTreeView *vista = GTK_TREE_VIEW(datos);
    GtkTreeSelection *seleccion = gtk_tree_view_get_selection(vista);
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    if (!gtk_tree_selection_get_selected(seleccion, &modelo, &iter)) {
        mostrar_mensaje(NULL, "Selecciona un Cliente de la lista primero.", TRUE);
        return;
    }
    gint id_cliente;
    gtk_tree_model_get(modelo, &iter, 0, &id_cliente, -1);

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Cambiar rol", NULL, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *combo = gtk_combo_box_text_new();
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "0", "Jefe");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "1", "Supervisor");
    gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), "2", "Administrador");
    gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
    gtk_container_set_border_width(GTK_CONTAINER(combo), 12);
    gtk_container_add(GTK_CONTAINER(area), combo);
    gtk_widget_show_all(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const gchar *id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(combo));
        RolCliente nuevo_rol = id_texto ? (RolCliente)atoi(id_texto) : ROL_CLIENTE_JEFE;
        if (cliente_actualizar_rol(id_cliente, nuevo_rol) == 0) {
            gtk_list_store_set(GTK_LIST_STORE(modelo), &iter, 2, cliente_rol_nombre(nuevo_rol), -1);
            mostrar_mensaje(NULL, "Rol actualizado.", FALSE);
        } else {
            mostrar_mensaje(NULL, "No se pudo actualizar el rol.", TRUE);
        }
    }
    gtk_widget_destroy(dialogo);
}

static void on_administrar_clientes_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;
    if (!d || d->rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Solo el Administrador puede administrar Clientes.", TRUE);
        return;
    }

    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "Administrar Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 520, 400);
    gtk_window_set_transient_for(GTK_WINDOW(ventana), padre);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER_ON_PARENT);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    GtkListStore *store = gtk_list_store_new(4, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    Cliente *lista = NULL;
    int n = 0;
    cliente_listar(&lista, &n);
    for (int i = 0; i < n; i++) {
        GtkTreeIter iter;
        gtk_list_store_append(store, &iter);
        gtk_list_store_set(store, &iter,
            0, lista[i].id,
            1, lista[i].nombre,
            2, cliente_rol_nombre(lista[i].rol),
            3, lista[i].correo,
            -1);
    }
    free(lista);

    GtkWidget *vista = gtk_tree_view_new_with_model(GTK_TREE_MODEL(store));
    g_object_unref(store);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Nombre", gtk_cell_renderer_text_new(), "text", 1, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Rol actual", gtk_cell_renderer_text_new(), "text", 2, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(vista), -1, "Correo", gtk_cell_renderer_text_new(), "text", 3, NULL);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_container_add(GTK_CONTAINER(scroll), vista);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *btn_cambiar = gtk_button_new_with_label("Cambiar rol del seleccionado");
    g_signal_connect(btn_cambiar, "clicked", G_CALLBACK(on_cambiar_rol_cliente_clicked), vista);
    gtk_box_pack_start(GTK_BOX(caja), btn_cambiar, FALSE, FALSE, 0);

    GtkWidget *btn_cerrar = gtk_button_new_with_label("Cerrar");
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);
    gtk_box_pack_start(GTK_BOX(caja), btn_cerrar, FALSE, FALSE, 0);

    gtk_widget_show_all(ventana);
}"""

ANCLA_ARREGLOS = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
        "Configurar Notificaciones",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
        "\\xF0\\x9F\\x91\\xA5", /* people */
        "\\xF0\\x9F\\x93\\xA7", /* envelope */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion",
    };
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
        G_CALLBACK(on_configurar_notificaciones_clicked),
    };
    const int total_modulos = 11;"""
NUEVO_ARREGLOS = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
        "Configurar Notificaciones",
        "Administrar Clientes",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
        "\\xF0\\x9F\\x91\\xA5", /* people */
        "\\xF0\\x9F\\x93\\xA7", /* envelope */
        "\\xF0\\x9F\\x9B\\x82", /* briefcase */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion", "cat-gestion",
    };
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
        G_CALLBACK(on_configurar_notificaciones_clicked),
        G_CALLBACK(on_administrar_clientes_clicked),
    };
    const int total_modulos = 12;"""


def main():
    archivos = [
        (ARCHIVO_DB_H, [(ANCLA_H, NUEVO_H, "declaracion cliente_actualizar_rol")]),
        (ARCHIVO_DB_C, [(ANCLA_C, NUEVO_C, "cliente_actualizar_rol")]),
        (ARCHIVO_GTK, [
            (ANCLA_GTK_CAMPOS, NUEVO_GTK_CAMPOS, "campos del formulario de registro"),
            (ANCLA_GTK_ACEPTAR, NUEVO_GTK_ACEPTAR, "manejo del boton Crear cuenta"),
            (ANCLA_PERMISOS, NUEVO_PERMISOS, "modulo_permitido + pantalla Administrar Clientes"),
            (ANCLA_ARREGLOS, NUEVO_ARREGLOS, "arreglos del dashboard"),
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
                print("       Puede que agregar-pantalla-notificaciones.py no se haya aplicado")
                print("       todavia, o que el archivo ya haya sido modificado. No se cambio nada.")
                sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, pares in archivos:
        contenido = contenidos[ruta]
        for ancla, nuevo, _nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak5")
        print(f"Backup creado: {ruta}.bak5")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Ahora compila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")


if __name__ == "__main__":
    main()
