#!/usr/bin/env python3
"""
agregar-boton-maximizar-real.py

El boton de maximizar/restaurar no aparecia porque el gestor de
ventanas de la VM no dibuja ese icono (queda un cuadro negro vacio), y
mientras la ventana esta maximizada asi (sin decoracion util), tampoco
hay borde que se pueda arrastrar para achicarla a mano.

La solucion de raiz: en vez de depender del gestor de ventanas, la app
dibuja su propia barra de titulo (con gtk_header_bar) con un boton de
maximizar/restaurar que funciona siempre, sin importar el tema del
gestor de ventanas. Se aplica al selector inicial y al menu principal
(las dos pantallas que se abren maximizadas).

No se toca ninguna logica: el boton solo alterna entre maximizar y
restaurar la misma ventana, nada mas.

Uso: parado en la raiz del repo:
    python3 agregar-boton-maximizar-real.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: funcion de apoyo para el boton (antes de mostrar_selector_entrada,
# junto a la otra funcion de apoyo que ya esta ahi)
# ---------------------------------------------------------------------------
ANCLA_HELPER = '''static gboolean revelar_pregunta_selector(gpointer datos) {
'''
NUEVO_HELPER = '''/* Alterna maximizar/restaurar la ventana que se le pase, y cambia el
 * icono del boton para que quede claro cual de las dos acciones toca.
 * Se usa en el selector inicial y en el menu principal -- ambos abren
 * maximizados, y el gestor de ventanas de algunas maquinas no dibuja
 * su propio boton de restaurar, asi que la app trae el suyo. */
static void on_click_maximizar_restaurar(GtkButton *boton, gpointer datos) {
    GtkWindow *ventana = GTK_WINDOW(datos);
    GtkWidget *imagen;
    if (gtk_window_is_maximized(ventana)) {
        gtk_window_unmaximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-maximize-symbolic", GTK_ICON_SIZE_BUTTON);
    } else {
        gtk_window_maximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON);
    }
    gtk_button_set_image(GTK_BUTTON(boton), imagen);
}

static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo) {
    GtkWidget *barra = gtk_header_bar_new();
    gtk_header_bar_set_title(GTK_HEADER_BAR(barra), titulo);
    gtk_header_bar_set_show_close_button(GTK_HEADER_BAR(barra), TRUE);

    GtkWidget *boton_maximizar = gtk_button_new();
    gtk_button_set_image(GTK_BUTTON(boton_maximizar),
        gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON));
    gtk_widget_set_tooltip_text(boton_maximizar, "Maximizar / Restaurar");
    g_signal_connect(boton_maximizar, "clicked", G_CALLBACK(on_click_maximizar_restaurar), ventana);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(barra), boton_maximizar);

    gtk_window_set_titlebar(ventana, barra);
    return barra;
}

static gboolean revelar_pregunta_selector(gpointer datos) {
'''

# ---------------------------------------------------------------------------
# Parche 2: selector inicial -> usa la barra de titulo propia
# ---------------------------------------------------------------------------
ANCLA_SELECTOR = '''    gtk_window_set_resizable(GTK_WINDOW(dialogo), TRUE);
    gtk_window_maximize(GTK_WINDOW(dialogo));
'''
NUEVO_SELECTOR = '''    gtk_window_set_resizable(GTK_WINDOW(dialogo), TRUE);
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(dialogo), "PawOS Refugio");
    gtk_window_maximize(GTK_WINDOW(dialogo));
'''

# ---------------------------------------------------------------------------
# Parche 3: menu principal -> usa la barra de titulo propia
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Parche 0: declaracion adelantada -- construir_ventana_principal aparece
# ANTES en el archivo que la funcion de apoyo, en C hace falta avisarle
# al compilador que existe antes de usarla.
# ---------------------------------------------------------------------------
ANCLA_DECLARACION = '''static void construir_ventana_principal(Rol rol, const char *usuario) {
'''
NUEVO_DECLARACION = '''static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo);

static void construir_ventana_principal(Rol rol, const char *usuario) {
'''

ANCLA_MENU = '''    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    gtk_window_maximize(GTK_WINDOW(ventana));
'''
NUEVO_MENU = '''    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_maximize(GTK_WINDOW(ventana));
'''

PARCHES = [
    ("declaracion adelantada", ANCLA_DECLARACION, NUEVO_DECLARACION),
    ("funcion de apoyo del boton", ANCLA_HELPER, NUEVO_HELPER),
    ("selector inicial (barra propia)", ANCLA_SELECTOR, NUEVO_SELECTOR),
    ("menu principal (barra propia)", ANCLA_MENU, NUEVO_MENU),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for nombre, ancla, _ in PARCHES:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1). No se cambio nada.")
            sys.exit(1)

    for _, ancla, nuevo in PARCHES:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak21")
    print(f"Backup creado: {ARCHIVO}.bak21")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: la app ya trae su propio boton de maximizar/restaurar.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
