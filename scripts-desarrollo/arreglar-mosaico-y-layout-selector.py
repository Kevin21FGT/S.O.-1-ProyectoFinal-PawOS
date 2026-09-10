#!/usr/bin/env python3
"""
arreglar-mosaico-y-layout-selector.py

Corrige el "mosaico" de la caja del titulo: el problema era que le
habiamos puesto la MISMA clase que usa el fondo grande (que carga su
propia copia de la imagen, recortada a su propio tamano chiquito) --
por eso se veian dos fotos distintas, no una sola. La solucion real es
dejar esa caja transparente, para que se vea la unica imagen grande de
"area" por debajo, sin cortes.

De paso, aplica lo que pediste: se quita el titulo "PawOS Refugio" de
arriba (ya sale dibujado en la imagen) y la pregunta "Como quieres
entrar?" se agrupa junto a los botones, cerca de la parte de abajo, en
vez de quedar pegada arriba con tanto espacio vacio en medio.

Uso: parado en la raiz del repo:
    python3 arreglar-mosaico-y-layout-selector.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: nueva clase CSS "pawos-fondo-transparente" (sin imagen propia,
# deja ver la de su contenedor de arriba)
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".pawos-fondo-dinamico entry, .pawos-fondo-dinamico textview,"
        ".pawos-fondo-dinamico textview text {"
        "  background-color: rgba(255,255,255,0.94);"
        "  color: #14301D;"
        "}"
'''
NUEVO_CSS = '''        ".pawos-fondo-dinamico entry, .pawos-fondo-dinamico textview,"
        ".pawos-fondo-dinamico textview text {"
        "  background-color: rgba(255,255,255,0.94);"
        "  color: #14301D;"
        "}"
        ".pawos-fondo-transparente {"
        "  background-color: transparent;"
        "  background-image: none;"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 2: selector inicial -> caja transparente, sin titulo, pegada abajo
# ---------------------------------------------------------------------------
ANCLA_SELECTOR = '''    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo),
        "<span size='xx-large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new("\\xC2\\xBF" "Como quieres entrar?");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);
'''
NUEVO_SELECTOR = '''    gtk_container_add(GTK_CONTAINER(area), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-transparente");
    /* La imagen ya trae el logo y el nombre "PawOS" dibujados, asi que
     * no repetimos el titulo aqui -- solo la pregunta, agrupada cerca
     * de los botones en vez de quedar pegada arriba. */
    gtk_widget_set_valign(caja, GTK_ALIGN_END);
    gtk_widget_set_vexpand(caja, TRUE);

    GtkWidget *subtitulo = gtk_label_new("\\xC2\\xBF" "Como quieres entrar?");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);
'''

# ---------------------------------------------------------------------------
# Parche 3: login de clientes -> misma correccion de transparencia
# ---------------------------------------------------------------------------
ANCLA_LOGIN = '''        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
'''
NUEVO_LOGIN = '''        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-transparente");
'''

PARCHES = [
    ("CSS pawos-fondo-transparente", ANCLA_CSS, NUEVO_CSS),
    ("selector inicial (sin titulo, agrupado abajo)", ANCLA_SELECTOR, NUEVO_SELECTOR),
    ("login de clientes (transparencia)", ANCLA_LOGIN, NUEVO_LOGIN),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak16")
    print(f"Backup creado: {ARCHIVO}.bak16")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
