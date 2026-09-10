#!/usr/bin/env python3
"""
arreglar-boton-maximizar.py

GTK crea los dialogos (gtk_dialog_new_with_buttons) con el "type hint"
de ventana normal de dialogo, y muchos gestores de ventanas ocultan el
boton de maximizar/restaurar en ese tipo de ventana (asumen que un
dialogo no se necesita maximizar). Para el selector inicial, que si
debe verse en pantalla completa CON boton de restaurar, se fuerza el
hint a ventana normal antes de maximizar.

Uso: parado en la raiz del repo:
    python3 arreglar-boton-maximizar.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_window_maximize(GTK_WINDOW(dialogo));

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''
NUEVO = '''    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    /* Sin esto el gestor de ventanas trata el dialogo como una ventana
     * simple y no muestra el boton de maximizar/restaurar. */
    gtk_window_set_type_hint(GTK_WINDOW(dialogo), GDK_WINDOW_TYPE_HINT_NORMAL);
    gtk_window_set_resizable(GTK_WINDOW(dialogo), TRUE);
    gtk_window_maximize(GTK_WINDOW(dialogo));

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque esperado se encontro {n} veces (se esperaba 1). No se cambio nada.")
        print("¿Ya corriste los parches anteriores del fondo dinamico?")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak14")
    print(f"Backup creado: {ARCHIVO}.bak14")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: el selector inicial ya deberia mostrar el boton de maximizar/restaurar.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
