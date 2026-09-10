#!/usr/bin/env python3
"""
mejorar-banner-titulo.py

El titulo/subtitulo ("PawOS Refugio" / "Como quieres entrar?") se ve en
una caja oscura solida separada de la imagen de fondo, en vez de flotar
sobre ella. Esto pasa porque esa caja ("caja") tambien hace match con la
regla vieja "dialog box { background-color: ... }" (cualquier caja
dentro de un dialogo). Se arregla agregandole la misma clase
"pawos-fondo-dinamico" (que por ser una clase le gana en especificidad
a esa regla vieja), asi la imagen se ve continua detras del texto.

Tambien se le agrega sombra al texto (para que resalte mas sobre la
imagen) y se agranda el titulo del selector inicial para que se vea
mas llamativo.

Uso: parado en la raiz del repo:
    python3 mejorar-banner-titulo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: sombra en el texto sobre el fondo dinamico (mas llamativo)
# ---------------------------------------------------------------------------
ANCLA_SOMBRA = '''        ".pawos-fondo-dinamico label { color: #FFFFFF; }"
'''
NUEVO_SOMBRA = '''        ".pawos-fondo-dinamico label {"
        "  color: #FFFFFF;"
        "  text-shadow: 0 2px 6px rgba(0,0,0,0.6);"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 2: selector inicial -> la caja del titulo tambien lleva la clase
# ---------------------------------------------------------------------------
ANCLA_SELECTOR = '''    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 16);
    gtk_container_add(GTK_CONTAINER(area), caja);
'''
NUEVO_SELECTOR = '''    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_style_context_add_class(gtk_widget_get_style_context(area), "pawos-fondo-dinamico");
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 16);
    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
'''

# ---------------------------------------------------------------------------
# Parche 3: agrandar el titulo del selector (mas llamativo)
# ancla mas larga (incluye la creacion del label) para que sea unica --
# esta misma frase con size='large' aparece en mas de un lugar del archivo.
# ---------------------------------------------------------------------------
ANCLA_TITULO = '''    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo),
        "<span size='large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);
'''
NUEVO_TITULO = '''    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo),
        "<span size='xx-large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);
'''

# ---------------------------------------------------------------------------
# Parche 4: login de clientes -> la caja del formulario tambien lleva la clase
# ---------------------------------------------------------------------------
ANCLA_LOGIN = '''        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_style_context_add_class(gtk_widget_get_style_context(area_contenido), "pawos-fondo-dinamico");
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
'''
NUEVO_LOGIN = '''        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_style_context_add_class(gtk_widget_get_style_context(area_contenido), "pawos-fondo-dinamico");
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
'''

PARCHES = [
    ("sombra en texto", ANCLA_SOMBRA, NUEVO_SOMBRA),
    ("caja del selector inicial", ANCLA_SELECTOR, NUEVO_SELECTOR),
    ("titulo mas grande", ANCLA_TITULO, NUEVO_TITULO),
    ("caja del login de clientes", ANCLA_LOGIN, NUEVO_LOGIN),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak15")
    print(f"Backup creado: {ARCHIVO}.bak15")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: titulo/subtitulo ya se ven sobre la imagen, con sombra y mas grande.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
