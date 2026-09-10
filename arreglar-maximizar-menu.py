#!/usr/bin/env python3
"""
Arregla el bug donde la ventana del menu principal ya no se puede
agrandar/maximizar despues del rediseño con secciones.

Causa: gtk_window_maximize() se llamaba justo despues de crear la barra
de titulo, ANTES de agregar el resto del contenido (banner, cuadricula
con las 3 cabeceras nuevas, botones). Al agregarse mas contenido, el
gestor de ventanas recalcula el tamaño DESPUES de haber pedido el
maximizado, y la ventana se queda chica sin poder agrandarse.

Arreglo: mover gtk_window_maximize() al final de la funcion, justo antes
de mostrar_con_fundido(ventana), cuando ya esta todo el contenido
agregado y el tamaño final ya se puede calcular bien. Tambien se agrega
gtk_window_set_resizable(TRUE) explicito (por seguridad, no cambia nada
si ya era TRUE) y se sube el tamaño por defecto de 580x660 a 900x700
como respaldo en caso de que el maximizado fallara en algun entorno.

No se toca ninguna logica de permisos, handlers ni orden de modulos.
"""
import shutil
import re
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_1 = '''    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 580, 660);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_maximize(GTK_WINDOW(ventana));
'''

NUEVO_1 = '''    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 900, 700);
    gtk_window_set_resizable(GTK_WINDOW(ventana), TRUE);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    agregar_barra_titulo_con_maximizar(GTK_WINDOW(ventana), "PawOS Refugio");
'''

ANCLA_2 = '''    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

    mostrar_con_fundido(ventana);
}'''

NUEVO_2 = '''    g_signal_connect_swapped(btn_salir, "clicked", G_CALLBACK(gtk_widget_destroy), ventana);

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

    for nombre, ancla in (("ANCLA_1", ANCLA_1), ("ANCLA_2", ANCLA_2)):
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: {nombre} aparece {n} veces (se esperaba 1). No se modifico nada.")
            sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA_1, NUEVO_1).replace(ANCLA_2, NUEVO_2)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Cambios aplicados:")
    print("  - gtk_window_maximize() movido al final de construir_ventana_principal()")
    print("  - gtk_window_set_resizable(TRUE) agregado explicitamente")
    print("  - Tamaño por defecto subido de 580x660 a 900x700")


if __name__ == "__main__":
    main()
