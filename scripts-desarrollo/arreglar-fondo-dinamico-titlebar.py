#!/usr/bin/env python3
"""
arreglar-fondo-dinamico-titlebar.py

Corrige un problema del parche anterior (agregar-fondo-dinamico.py): el
degradado se habia puesto en la ventana del dialogo completa, y eso
pintaba tambien la barra de titulo que dibuja el sistema (se veia un
recuadro verde flotando arriba, separado y duplicado con el titulo de
adentro). Ademas, por estar en el nodo equivocado, el degradado no
cubria bien el contenido del dialogo (se veia "plano").

Este parche mueve la clase "pawos-fondo-dinamico" de la ventana del
dialogo hacia su area de contenido (el mismo patron que ya usa el menu
principal con "caja", que por eso no tuvo este problema). Tambien
simplifica el CSS para que ya no incluya el selector "dialog" (solo
hacia falta para el nodo de ventana, que ya no vamos a estilizar).

Requiere haber corrido agregar-fondo-dinamico.py antes.

Uso: parado en la raiz del repo:
    python3 arreglar-fondo-dinamico-titlebar.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: simplificar el selector CSS (ya no se necesita "dialog")
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        "dialog.pawos-fondo-dinamico, dialog.pawos-fondo-dinamico box,"
        ".pawos-fondo-dinamico {"
'''
NUEVO_CSS = '''        ".pawos-fondo-dinamico {"
'''

# ---------------------------------------------------------------------------
# Parche 2: registro de clientes -> mover la clase a "area"
# ---------------------------------------------------------------------------
ANCLA_REGISTRO = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
'''
NUEVO_REGISTRO = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *grid = gtk_grid_new();
'''

# ---------------------------------------------------------------------------
# Parche 3: login de clientes -> mover la clase a "area_contenido"
# ---------------------------------------------------------------------------
ANCLA_LOGIN = '''        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
        gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");

        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
'''
NUEVO_LOGIN = '''        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_style_context_add_class(gtk_widget_get_style_context(area_contenido), "pawos-fondo-dinamico");
'''

# ---------------------------------------------------------------------------
# Parche 4: selector inicial -> mover la clase a "area" (se queda maximizado)
# ---------------------------------------------------------------------------
ANCLA_SELECTOR = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");
    gtk_window_maximize(GTK_WINDOW(dialogo));

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''
NUEVO_SELECTOR = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_window_maximize(GTK_WINDOW(dialogo));

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''

PARCHES = [
    ("CSS (quitar selector 'dialog')", ANCLA_CSS, NUEVO_CSS),
    ("registro de clientes", ANCLA_REGISTRO, NUEVO_REGISTRO),
    ("login de clientes", ANCLA_LOGIN, NUEVO_LOGIN),
    ("selector inicial", ANCLA_SELECTOR, NUEVO_SELECTOR),
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
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("¿Ya corriste agregar-fondo-dinamico.py antes que este? No se cambio nada.")
            sys.exit(1)

    for _, ancla, nuevo in PARCHES:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak12")
    print(f"Backup creado: {ARCHIVO}.bak12")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: el degradado ya no toca la barra de titulo.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
