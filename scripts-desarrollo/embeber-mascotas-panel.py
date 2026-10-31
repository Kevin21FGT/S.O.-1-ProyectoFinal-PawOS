#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Piloto: convierte "Gestion de Mascotas" de ventana emergente a panel
embebido en el area de contenido del menu principal (a la derecha de
la barra lateral), en vez de abrir una ventana nueva encima.

No se toca la logica de negocio: on_registrar_clicked, on_cambiar_estado_clicked
y on_eliminar_clicked quedan exactamente igual (solo usan ctx->ventana
como padre de sus propios sub-dialogos, nunca para meterle contenido
adentro, asi que no hacia falta cambiarlos).

Cambios:
  1. DatosBotonModulo gana un campo nuevo: area_dinamica.
  2. Se agregan 3 funciones chicas antes de abrir_pantalla_mascotas:
     - mostrar_en_panel(): vacia un contenedor y le mete contenido nuevo.
     - construir_tarjeta_bienvenida(): la tarjeta de bienvenida, ahora
       reutilizable (se muestra al inicio y al volver de un modulo).
     - on_cerrar_panel_clicked(): el boton "Cerrar" ahora vuelve a la
       tarjeta de bienvenida en vez de destruir una ventana.
  3. abrir_pantalla_mascotas ya no crea gtk_window_new(): arma la misma
     tabla + botones de siempre y los mete en area_dinamica. ctx->ventana
     ahora apunta a la ventana principal (unicamente para que los
     sub-dialogos de Registrar/Cambiar estado/Eliminar tengan un padre
     valido, igual que antes).
  4. on_mascotas_clicked pasa el area_dinamica ademas de lo que ya pasaba.
  5. construir_ventana_principal: la tarjeta de bienvenida ahora vive
     dentro de un contenedor "area_dinamica" que se puede vaciar y
     rellenar, y datos_botones->area_dinamica queda apuntando a el.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

# ---------------------------------------------------------------------
# 1) DatosBotonModulo: agregar campo area_dinamica
# ---------------------------------------------------------------------
ANCLA_STRUCT = r'''typedef struct {
    GtkWidget  *ventana_principal;
    Rol         rol;
    const char *usuario;
} DatosBotonModulo;'''

NUEVO_STRUCT = r'''typedef struct {
    GtkWidget  *ventana_principal;
    GtkWidget  *area_dinamica;
    Rol         rol;
    const char *usuario;
} DatosBotonModulo;'''

# ---------------------------------------------------------------------
# 2) on_mascotas_clicked: pasar el area_dinamica tambien
# ---------------------------------------------------------------------
ANCLA_CLICK = r'''static void on_mascotas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_mascotas(d->ventana_principal, d->rol);
}'''

NUEVO_CLICK = r'''static void on_mascotas_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    abrir_pantalla_mascotas(d->area_dinamica, d->ventana_principal, d->rol);
}'''

# ---------------------------------------------------------------------
# 3) abrir_pantalla_mascotas: de ventana propia a panel embebido,
#    mas las 3 funciones auxiliares nuevas justo antes.
# ---------------------------------------------------------------------
ANCLA_ABRIR = r'''static void abrir_pantalla_mascotas(GtkWidget *padre, Rol rol) {
    ContextoMascotas *ctx = g_malloc0(sizeof(ContextoMascotas));
    ctx->rol = rol;

    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Gestion de Mascotas");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 760, 480);
    gtk_window_set_transient_for(GTK_WINDOW(ctx->ventana), GTK_WINDOW(padre));
    gtk_container_set_border_width(GTK_CONTAINER(ctx->ventana), 14);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Gestion de Mascotas</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_MASCOTAS,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_MASCOTAS] = {"ID", "Nombre", "Especie", "Raza", "Edad", "Estado", "Ingreso"};
    for (int i = 0; i < N_COL_MASCOTAS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar nueva");
    GtkWidget *btn_estado    = gtk_button_new_with_label("Cambiar estado");
    GtkWidget *btn_eliminar  = gtk_button_new_with_label("Eliminar");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_eliminar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que en pantallas.c (CLI): el voluntario solo ve y registra,
     * no cambia estado ni elimina. El boton se muestra siempre, pero
     * queda deshabilitado (no oculto) para que se note que la opcion
     * existe aunque el rol actual no pueda usarla. */
    if (rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(btn_estado, FALSE);
        gtk_widget_set_sensitive(btn_eliminar, FALSE);
        gtk_widget_set_tooltip_text(btn_estado, "Requiere rol Admin o Veterinario.");
        gtk_widget_set_tooltip_text(btn_eliminar, "Requiere rol Admin o Veterinario.");
    }

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_mascotas_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_clicked), ctx);
    g_signal_connect(btn_estado, "clicked", G_CALLBACK(on_cambiar_estado_clicked), ctx);
    g_signal_connect(btn_eliminar, "clicked", G_CALLBACK(on_eliminar_clicked), ctx);
    g_signal_connect_swapped(btn_cerrar, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(liberar_contexto), ctx);

    cargar_mascotas(ctx);
    mostrar_con_fundido(ctx->ventana);
}'''

NUEVO_ABRIR = r'''static void mostrar_en_panel(GtkWidget *contenedor, GtkWidget *nuevo) {
    GList *hijos = gtk_container_get_children(GTK_CONTAINER(contenedor));
    for (GList *l = hijos; l != NULL; l = l->next) {
        gtk_widget_destroy(GTK_WIDGET(l->data));
    }
    g_list_free(hijos);
    gtk_container_add(GTK_CONTAINER(contenedor), nuevo);
    gtk_widget_show_all(nuevo);
}

static GtkWidget *construir_tarjeta_bienvenida(void) {
    GtkWidget *tarjeta_bienvenida = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_bienvenida), "pawos-tarjeta");

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_ayuda = gtk_label_new("Selecciona un modulo del menu lateral para comenzar.");
    gtk_widget_set_halign(lbl_ayuda, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), lbl_ayuda, FALSE, FALSE, 0);

    return tarjeta_bienvenida;
}

static void on_cerrar_panel_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWidget *area_dinamica = GTK_WIDGET(datos);
    mostrar_en_panel(area_dinamica, construir_tarjeta_bienvenida());
}

/* "Gestion de Mascotas" ahora se dibuja directamente en el panel de
 * contenido del menu principal (area_dinamica), en vez de abrir una
 * ventana nueva encima. ctx->ventana sigue existiendo, pero ahora
 * apunta a la ventana principal -- solo se usa como padre de los
 * sub-dialogos de Registrar/Cambiar estado/Eliminar (esas tres
 * funciones no cambiaron ni una linea). */
static void abrir_pantalla_mascotas(GtkWidget *area_dinamica, GtkWidget *ventana_principal, Rol rol) {
    ContextoMascotas *ctx = g_malloc0(sizeof(ContextoMascotas));
    ctx->rol = rol;
    ctx->ventana = ventana_principal;

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    /* El contexto se libera solo cuando este panel se reemplaza por
     * otro (mostrar_en_panel destruye "caja"), sin depender de que se
     * cierre ninguna ventana. */
    g_object_set_data_full(G_OBJECT(caja), "pawos-contexto-mascotas", ctx, g_free);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='large' weight='bold'>Gestion de Mascotas</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    ctx->store = gtk_list_store_new(N_COL_MASCOTAS,
        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING,
        G_TYPE_STRING, G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING);
    ctx->treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store));
    g_object_unref(ctx->store);

    const char *encabezados[N_COL_MASCOTAS] = {"ID", "Nombre", "Especie", "Raza", "Edad", "Estado", "Ingreso"};
    for (int i = 0; i < N_COL_MASCOTAS; i++) {
        GtkCellRenderer *render = gtk_cell_renderer_text_new();
        GtkTreeViewColumn *col = gtk_tree_view_column_new_with_attributes(
            encabezados[i], render, "text", i, NULL);
        gtk_tree_view_column_set_resizable(col, TRUE);
        gtk_tree_view_append_column(GTK_TREE_VIEW(ctx->treeview), col);
    }

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_container_add(GTK_CONTAINER(scroll), ctx->treeview);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *fila_botones = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), fila_botones, FALSE, FALSE, 0);

    GtkWidget *btn_refrescar = gtk_button_new_with_label("Actualizar lista");
    GtkWidget *btn_registrar = gtk_button_new_with_label("Registrar nueva");
    GtkWidget *btn_estado    = gtk_button_new_with_label("Cambiar estado");
    GtkWidget *btn_eliminar  = gtk_button_new_with_label("Eliminar");
    GtkWidget *btn_cerrar    = gtk_button_new_with_label("Cerrar");

    gtk_box_pack_start(GTK_BOX(fila_botones), btn_refrescar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_registrar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_estado, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_eliminar, FALSE, FALSE, 0);
    gtk_box_pack_end(GTK_BOX(fila_botones), btn_cerrar, FALSE, FALSE, 0);

    /* Igual que en pantallas.c (CLI): el voluntario solo ve y registra,
     * no cambia estado ni elimina. El boton se muestra siempre, pero
     * queda deshabilitado (no oculto) para que se note que la opcion
     * existe aunque el rol actual no pueda usarla. */
    if (rol == ROL_VOLUNTARIO) {
        gtk_widget_set_sensitive(btn_estado, FALSE);
        gtk_widget_set_sensitive(btn_eliminar, FALSE);
        gtk_widget_set_tooltip_text(btn_estado, "Requiere rol Admin o Veterinario.");
        gtk_widget_set_tooltip_text(btn_eliminar, "Requiere rol Admin o Veterinario.");
    }

    g_signal_connect(btn_refrescar, "clicked", G_CALLBACK(on_refrescar_mascotas_clicked), ctx);
    g_signal_connect(btn_registrar, "clicked", G_CALLBACK(on_registrar_clicked), ctx);
    g_signal_connect(btn_estado, "clicked", G_CALLBACK(on_cambiar_estado_clicked), ctx);
    g_signal_connect(btn_eliminar, "clicked", G_CALLBACK(on_eliminar_clicked), ctx);
    g_signal_connect(btn_cerrar, "clicked", G_CALLBACK(on_cerrar_panel_clicked), area_dinamica);

    cargar_mascotas(ctx);
    mostrar_en_panel(area_dinamica, caja);
}'''

# ---------------------------------------------------------------------
# 4) construir_ventana_principal: envolver la tarjeta de bienvenida en
#    un area_dinamica reemplazable, y guardarla en datos_botones.
# ---------------------------------------------------------------------
ANCLA_PANEL = r'''    GtkWidget *tarjeta_bienvenida = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_bienvenida), "pawos-tarjeta");
    gtk_box_pack_start(GTK_BOX(panel_contenido), tarjeta_bienvenida, FALSE, FALSE, 0);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo), "<span size='x-large' weight='bold'>\xF0\x9F\x90\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), titulo, FALSE, FALSE, 0);

    GtkWidget *lbl_ayuda = gtk_label_new("Selecciona un modulo del menu lateral para comenzar.");
    gtk_widget_set_halign(lbl_ayuda, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(tarjeta_bienvenida), lbl_ayuda, FALSE, FALSE, 0);

    /* Maximizamos al final, ya con todo el contenido agregado, para que
     * el gestor de ventanas calcule el tamaño definitivo antes de pedir
     * el maximizado (evita que quede una ventana pequeña sin poder
     * agrandarse). */
    gtk_window_maximize(GTK_WINDOW(ventana));
    mostrar_con_fundido(ventana);
}'''

NUEVO_PANEL = r'''    /* area_dinamica es el contenedor que se vacia y se vuelve a llenar
     * cada vez que se entra a un modulo o se vuelve al inicio -- por
     * ahora solo "Gestion de Mascotas" lo usa (piloto), el resto de
     * modulos sigue abriendo su propia ventana como antes. */
    GtkWidget *area_dinamica = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_widget_set_vexpand(area_dinamica, TRUE);
    gtk_widget_set_hexpand(area_dinamica, TRUE);
    gtk_box_pack_start(GTK_BOX(panel_contenido), area_dinamica, TRUE, TRUE, 0);
    gtk_container_add(GTK_CONTAINER(area_dinamica), construir_tarjeta_bienvenida());
    datos_botones->area_dinamica = area_dinamica;

    /* Maximizamos al final, ya con todo el contenido agregado, para que
     * el gestor de ventanas calcule el tamaño definitivo antes de pedir
     * el maximizado (evita que quede una ventana pequeña sin poder
     * agrandarse). */
    gtk_window_maximize(GTK_WINDOW(ventana));
    mostrar_con_fundido(ventana);
}'''


def siguiente_backup(ruta: Path) -> Path:
    n = 1
    while True:
        candidato = ruta.with_name(ruta.name + f".bak{n}")
        if not candidato.exists():
            return candidato
        n += 1


def main():
    if not ARCHIVO.exists():
        print(f"ERROR: no se encontro {ARCHIVO}. Ejecuta este script desde la raiz del repo.")
        sys.exit(1)

    contenido = ARCHIVO.read_text(encoding="utf-8")

    anclas = [
        ("ANCLA_STRUCT", ANCLA_STRUCT),
        ("ANCLA_CLICK", ANCLA_CLICK),
        ("ANCLA_ABRIR", ANCLA_ABRIR),
        ("ANCLA_PANEL", ANCLA_PANEL),
    ]
    for nombre, ancla in anclas:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: {nombre} aparece {n} veces (se esperaba 1). No se modifico nada.")
            sys.exit(1)

    nuevo_contenido = (
        contenido
        .replace(ANCLA_STRUCT, NUEVO_STRUCT)
        .replace(ANCLA_CLICK, NUEVO_CLICK)
        .replace(ANCLA_ABRIR, NUEVO_ABRIR)
        .replace(ANCLA_PANEL, NUEVO_PANEL)
    )

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Cambios aplicados:")
    print("  - Gestion de Mascotas ahora se muestra embebida en el panel derecho")
    print("  - Registrar nueva / Cambiar estado / Eliminar quedaron intactos")
    print("  - Boton Cerrar ahora vuelve a la pantalla de bienvenida")


if __name__ == "__main__":
    main()
