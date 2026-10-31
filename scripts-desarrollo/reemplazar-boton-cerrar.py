#!/usr/bin/env python3
"""
reemplazar-boton-cerrar.py

El boton de cerrar (X) que GTK agrega automaticamente con
gtk_header_bar_set_show_close_button() trae un cuadro de fondo feo que
no se puede quitar por CSS -- lo mas probable es que sea el icono del
tema de esa maquina, no un fondo real. Se reemplaza por un boton propio
con una "x" de texto (igual que ya se hizo con el de maximizar), asi
se controla exactamente como se ve, sin depender del tema de iconos
del sistema.

Uso: parado en la raiz del repo:
    python3 reemplazar-boton-cerrar.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo) {
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
'''
NUEVO = '''static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo) {
    GtkWidget *barra = gtk_header_bar_new();
    gtk_header_bar_set_title(GTK_HEADER_BAR(barra), titulo);

    GtkWidget *boton_maximizar = gtk_button_new();
    gtk_button_set_image(GTK_BUTTON(boton_maximizar),
        gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON));
    gtk_widget_set_tooltip_text(boton_maximizar, "Maximizar / Restaurar");
    g_signal_connect(boton_maximizar, "clicked", G_CALLBACK(on_click_maximizar_restaurar), ventana);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(barra), boton_maximizar);

    /* Boton de cerrar propio, de texto -- el que agrega GTK automatico
     * depende del icono del sistema, y en algunas maquinas se ve con
     * un cuadro de fondo feo que no se puede arreglar por CSS. */
    GtkWidget *boton_cerrar = gtk_button_new_with_label("\\xC3\\x97");
    gtk_style_context_add_class(gtk_widget_get_style_context(boton_cerrar), "pawos-boton-cerrar-barra");
    gtk_widget_set_tooltip_text(boton_cerrar, "Cerrar");
    g_signal_connect_swapped(boton_cerrar, "clicked", G_CALLBACK(gtk_window_close), ventana);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(barra), boton_cerrar);

    gtk_window_set_titlebar(ventana, barra);
    return barra;
}
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
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak24")
    print(f"Backup creado: {ARCHIVO}.bak24")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: boton de cerrar propio (sin depender del icono del sistema).")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
