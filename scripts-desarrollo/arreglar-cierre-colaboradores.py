#!/usr/bin/env python3
"""
arreglar-cierre-colaboradores.py

Bug real de memoria: en abrir_pantalla_administrar_colaboradores(), la
senal "destroy" de la ventana estaba conectada con g_signal_connect()
en vez de g_signal_connect_swapped(). Con g_signal_connect() normal,
GTK llama al callback como g_free(ventana, ctx) -- es decir, intenta
liberar el widget de la ventana con g_free() en vez de liberar "ctx"
(la estructura de datos interna), lo cual corrompe la memoria (por
eso el comportamiento era inconsistente: a veces "free(): invalid
pointer" y crash inmediato, otras veces el programa quedaba en un
estado invalido y se cerraba solo mas adelante).

Fix: usar g_signal_connect_swapped(), que intercambia el orden de los
argumentos y llama correctamente a g_free(ctx).

Requisito: correr DESPUES de agregar-administrar-colaboradores.py.

Uso: parado en la raiz del repo:
    python3 arreglar-cierre-colaboradores.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """    g_signal_connect(ventana, "destroy", G_CALLBACK(g_free), ctx);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    ctx->store = gtk_list_store_new(2, G_TYPE_STRING, G_TYPE_STRING);"""
NUEVO = """    /* g_signal_connect_swapped (no g_signal_connect normal): asi GTK
     * llama g_free(ctx) directo. Con g_signal_connect normal el
     * callback recibe (ventana, ctx) y terminaria intentando liberar
     * la ventana misma con g_free(), lo cual corrompe la memoria. */
    g_signal_connect_swapped(ventana, "destroy", G_CALLBACK(g_free), ctx);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(ventana), caja);

    ctx->store = gtk_list_store_new(2, G_TYPE_STRING, G_TYPE_STRING);"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque esperado.")
        print("       Puede que agregar-administrar-colaboradores.py no se haya aplicado todavia,")
        print("       o que el archivo ya haya sido modificado. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak13")
    print(f"Backup creado: {ARCHIVO}.bak13")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora:  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
