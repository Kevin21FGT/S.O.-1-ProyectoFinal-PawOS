#!/usr/bin/env python3
"""
mover-bienvenida-a-barra.py

El texto "Bienvenid@ a PawOS" quedaba flotando justo encima del logo de
la huella que ya trae la imagen (se veian encimados, raro). Se mueve a
la misma barra de abajo donde despues aparece la pregunta -- mismo
lugar, mismo estilo -- para que la transicion se sienta como una sola
barra que cambia de texto, no dos elementos distintos.

De paso, se le da mas pulido a esa barra: esquinas redondeadas arriba
y una sombra suave que la separa mejor de la imagen.

Uso: parado en la raiz del repo:
    python3 mover-bienvenida-a-barra.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: mas pulido en la barra inferior (esquinas + sombra)
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".pawos-panel-inferior {"
        "  background-color: rgba(8,38,18,0.55);"
        "  padding: 14px 20px;"
        "}"
'''
NUEVO_CSS = '''        ".pawos-panel-inferior {"
        "  background-color: rgba(8,38,18,0.6);"
        "  padding: 16px 20px;"
        "  border-radius: 18px 18px 0 0;"
        "  box-shadow: 0 -6px 16px rgba(0,0,0,0.3);"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 2: el revelador de bienvenida usa la misma barra de abajo
# (en vez de texto flotando en medio de la pantalla, sobre el logo)
# ---------------------------------------------------------------------------
ANCLA_BIENVENIDA = '''    GtkWidget *bienvenida = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(bienvenida),
        "<span size='xx-large' weight='bold'>Bienvenid@ a PawOS</span>");
    gtk_widget_set_halign(bienvenida, GTK_ALIGN_CENTER);
    gtk_container_add(GTK_CONTAINER(revelador_bienvenida), bienvenida);
    gtk_widget_set_valign(revelador_bienvenida, GTK_ALIGN_CENTER);
    gtk_widget_set_halign(revelador_bienvenida, GTK_ALIGN_CENTER);
    gtk_widget_set_vexpand(revelador_bienvenida, TRUE);
'''
NUEVO_BIENVENIDA = '''    GtkWidget *bienvenida = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(bienvenida),
        "<span size='x-large' weight='bold'>Bienvenid@ a PawOS</span>");
    gtk_label_set_xalign(GTK_LABEL(bienvenida), 0.5);
    gtk_widget_set_halign(bienvenida, GTK_ALIGN_FILL);
    gtk_style_context_add_class(gtk_widget_get_style_context(bienvenida), "pawos-panel-inferior");
    gtk_container_add(GTK_CONTAINER(revelador_bienvenida), bienvenida);
    /* Misma barra de abajo donde despues aparece la pregunta, para que
     * no quede flotando encima del logo de la imagen. */
    gtk_widget_set_valign(revelador_bienvenida, GTK_ALIGN_END);
    gtk_widget_set_halign(revelador_bienvenida, GTK_ALIGN_FILL);
    gtk_widget_set_vexpand(revelador_bienvenida, TRUE);
'''

PARCHES = [
    ("barra inferior mas pulida", ANCLA_CSS, NUEVO_CSS),
    ("bienvenida en la barra de abajo", ANCLA_BIENVENIDA, NUEVO_BIENVENIDA),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak19")
    print(f"Backup creado: {ARCHIVO}.bak19")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
