#!/usr/bin/env python3
"""
agregar-fondo-colaborador.py

Agrega el fondo dinamico (imagen de oficina + tinte verde) tambien al
login de Colaborador, con el mismo patron ya probado en las otras 4
pantallas: la imagen va en la ruta instalada si existe (.deb), o en el
repo si esta en modo desarrollo; la caja del formulario queda
transparente para que se vea una sola imagen continua, sin mosaico.

Requisitos antes de correr esto:
  1. Copiar la imagen a branding/fondo-colaborador.png

Uso: parado en la raiz del repo:
    python3 agregar-fondo-colaborador.py
"""

import os
import shutil
import sys

ARCHIVO_C = "src/main_gtk.c"
ARCHIVO_DEB = "construir-deb.sh"
IMAGEN = "branding/fondo-colaborador.png"

# ---------------------------------------------------------------------------
# Parche 1: instalar la imagen en el .deb
# ---------------------------------------------------------------------------
ANCLA_DEB = '''[ -f branding/fondo-bienvenida.png ] && install -m 644 branding/fondo-bienvenida.png "$RAIZ/usr/share/icons/fondo-bienvenida.png"
'''
NUEVO_DEB = '''[ -f branding/fondo-bienvenida.png ] && install -m 644 branding/fondo-bienvenida.png "$RAIZ/usr/share/icons/fondo-bienvenida.png"

[ -f branding/fondo-colaborador.png ] && install -m 644 branding/fondo-colaborador.png "$RAIZ/usr/share/icons/fondo-colaborador.png"
'''

# ---------------------------------------------------------------------------
# Parche 2: nueva variable con la ruta de la imagen (dentro de aplicar_estilos)
# ---------------------------------------------------------------------------
ANCLA_VAR = '''    const char *ruta_fondo_bienvenida =
        g_file_test("/usr/share/icons/fondo-bienvenida.png", G_FILE_TEST_EXISTS)
            ? "/usr/share/icons/fondo-bienvenida.png"
            : "branding/fondo-bienvenida.png";
'''
NUEVO_VAR = '''    const char *ruta_fondo_bienvenida =
        g_file_test("/usr/share/icons/fondo-bienvenida.png", G_FILE_TEST_EXISTS)
            ? "/usr/share/icons/fondo-bienvenida.png"
            : "branding/fondo-bienvenida.png";

    /* Imagen de fondo del login de Colaborador (oficina, distinta a la
     * de las pantallas de cliente). Mismo patron de ruta instalada vs
     * ruta del repo. */
    const char *ruta_fondo_colaborador =
        g_file_test("/usr/share/icons/fondo-colaborador.png", G_FILE_TEST_EXISTS)
            ? "/usr/share/icons/fondo-colaborador.png"
            : "branding/fondo-colaborador.png";
'''

# ---------------------------------------------------------------------------
# Parche 3: CSS -- nueva clase .pawos-fondo-colaborador
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
        ".pawos-fondo-colaborador {"
        "  background-image: linear-gradient(rgba(14,61,30,0.55), rgba(18,69,31,0.55)), url(\\"%s\\");"
        "  background-size: cover;"
        "  background-position: center;"
        "  background-repeat: no-repeat;"
        "}"
        ".pawos-fondo-colaborador label {"
        "  color: #FFFFFF;"
        "  text-shadow: 0 2px 6px rgba(0,0,0,0.6);"
        "}"
        ".pawos-fondo-colaborador entry, .pawos-fondo-colaborador textview,"
        ".pawos-fondo-colaborador textview text {"
        "  background-color: rgba(255,255,255,0.94);"
        "  color: #14301D;"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 4: agregar el nuevo argumento en la posicion correcta del
# g_strdup_printf (justo despues de ruta_fondo_bienvenida)
# ---------------------------------------------------------------------------
ANCLA_ARG = '''        ruta_fondo_bienvenida,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
'''
NUEVO_ARG = '''        ruta_fondo_bienvenida,
        ruta_fondo_colaborador,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
'''

# ---------------------------------------------------------------------------
# Parche 5: login de Colaborador -> usar la nueva clase
# ---------------------------------------------------------------------------
ANCLA_LOGIN = '''        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area_contenido), caja);
'''
NUEVO_LOGIN = '''        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_style_context_add_class(gtk_widget_get_style_context(area_contenido), "pawos-fondo-colaborador");
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area_contenido), caja);
        gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-transparente");
'''

PARCHES_C = [
    ("variable de ruta de imagen colaborador", ANCLA_VAR, NUEVO_VAR),
    ("CSS pawos-fondo-colaborador", ANCLA_CSS, NUEVO_CSS),
    ("argumento nuevo en g_strdup_printf", ANCLA_ARG, NUEVO_ARG),
    ("login de colaborador (usa la clase)", ANCLA_LOGIN, NUEVO_LOGIN),
]


def main():
    if not os.path.isfile(IMAGEN):
        print(f"ERROR: no encuentro {IMAGEN}.")
        print("Copia primero la imagen ahi y vuelve a correr esto.")
        sys.exit(1)

    try:
        with open(ARCHIVO_DEB, "r", encoding="utf-8") as f:
            deb = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_DEB}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = deb.count(ANCLA_DEB)
    if n != 1:
        print(f"ERROR: el bloque de instalacion de fondo-bienvenida se encontro {n} veces (se esperaba 1).")
        sys.exit(1)

    try:
        with open(ARCHIVO_C, "r", encoding="utf-8") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_C}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for nombre, ancla, _ in PARCHES_C:
        n = codigo.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1). No se cambio nada.")
            sys.exit(1)

    deb = deb.replace(ANCLA_DEB, NUEVO_DEB, 1)
    shutil.copy(ARCHIVO_DEB, ARCHIVO_DEB + ".bak3")
    print(f"Backup creado: {ARCHIVO_DEB}.bak3")
    with open(ARCHIVO_DEB, "w", encoding="utf-8") as f:
        f.write(deb)
    print(f"{ARCHIVO_DEB} parchado OK.")

    for _, ancla, nuevo in PARCHES_C:
        codigo = codigo.replace(ancla, nuevo, 1)
    shutil.copy(ARCHIVO_C, ARCHIVO_C + ".bak26")
    print(f"Backup creado: {ARCHIVO_C}.bak26")
    with open(ARCHIVO_C, "w", encoding="utf-8") as f:
        f.write(codigo)
    print(f"{ARCHIVO_C} parchado OK: login de Colaborador ya tiene su fondo dinamico.")

    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
