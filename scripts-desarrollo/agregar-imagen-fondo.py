#!/usr/bin/env python3
"""
agregar-imagen-fondo.py

Reemplaza el degradado plano del fondo dinamico por la ilustracion de
PawOS (bosque con los animales y el letrero "RESCUE"), con un tinte
verde semitransparente encima para que el texto blanco se siga leyendo
bien y para que respete la paleta de colores del programa.

Sigue el mismo patron que ya usa el icono de la app (branding/pawos-icon.png
-> /usr/share/icons/pawos-icon.png, con fallback a la ruta del repo si no
esta instalado):

  - Imagen fuente:   branding/fondo-bienvenida.png   (debes copiarla ahi)
  - Imagen instalada: /usr/share/icons/fondo-bienvenida.png (via el .deb)

Requisitos antes de correr esto:
  1. Ya haber corrido agregar-fondo-dinamico.py y arreglar-fondo-dinamico-titlebar.py
  2. Haber copiado la imagen a branding/fondo-bienvenida.png

Uso: parado en la raiz del repo:
    python3 agregar-imagen-fondo.py
"""

import os
import shutil
import sys

ARCHIVO_C = "src/main_gtk.c"
ARCHIVO_DEB = "construir-deb.sh"
IMAGEN = "branding/fondo-bienvenida.png"

# ---------------------------------------------------------------------------
# Parche 1: instalar la imagen en el .deb (construir-deb.sh)
# ---------------------------------------------------------------------------
ANCLA_DEB = '''[ -f branding/pawos-icon.png ] && install -m 644 branding/pawos-icon.png "$RAIZ/usr/share/icons/pawos-icon.png"
'''
NUEVO_DEB = '''[ -f branding/pawos-icon.png ] && install -m 644 branding/pawos-icon.png "$RAIZ/usr/share/icons/pawos-icon.png"

[ -f branding/fondo-bienvenida.png ] && install -m 644 branding/fondo-bienvenida.png "$RAIZ/usr/share/icons/fondo-bienvenida.png"
'''

# ---------------------------------------------------------------------------
# Parche 2: nueva variable con la ruta de la imagen (dentro de aplicar_estilos)
# ---------------------------------------------------------------------------
ANCLA_VAR = '''    const char *boton_borde      = oscuro ? "#3A443B" : "#D7DEDA";
'''
NUEVO_VAR = '''    const char *boton_borde      = oscuro ? "#3A443B" : "#D7DEDA";

    /* Imagen de fondo de las pantallas de bienvenida: usa la ruta instalada
     * si existe (.deb), si no cae al archivo del repo (modo desarrollo). */
    const char *ruta_fondo_bienvenida =
        g_file_test("/usr/share/icons/fondo-bienvenida.png", G_FILE_TEST_EXISTS)
            ? "/usr/share/icons/fondo-bienvenida.png"
            : "branding/fondo-bienvenida.png";
'''

# ---------------------------------------------------------------------------
# Parche 3: CSS -- usar la imagen (con tinte verde encima) en vez del degradado
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".pawos-fondo-dinamico {"
        "  background-image: linear-gradient(160deg, #0E3D1E 0%%, #16632F 35%%, #23924B 68%%, #3FBE79 100%%);"
        "}"
'''
NUEVO_CSS = '''        ".pawos-fondo-dinamico {"
        "  background-image: linear-gradient(rgba(14,61,30,0.55), rgba(18,69,31,0.55)), url(\\"%s\\");"
        "  background-size: cover;"
        "  background-position: center;"
        "  background-repeat: no-repeat;"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 4: agregar el nuevo argumento a la lista del g_strdup_printf,
# justo en la posicion que le corresponde al %s de arriba.
# ---------------------------------------------------------------------------
ANCLA_ARG = '''        boton_bg, boton_fg,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
'''
NUEVO_ARG = '''        boton_bg, boton_fg,
        ruta_fondo_bienvenida,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
'''

PARCHES_C = [
    ("variable de ruta de imagen", ANCLA_VAR, NUEVO_VAR),
    ("CSS con imagen de fondo", ANCLA_CSS, NUEVO_CSS),
    ("argumento nuevo en g_strdup_printf", ANCLA_ARG, NUEVO_ARG),
]


def main():
    if not os.path.isfile(IMAGEN):
        print(f"ERROR: no encuentro {IMAGEN}.")
        print("Copia primero la imagen ahi (crea la carpeta branding/ si no existe) y vuelve a correr esto.")
        sys.exit(1)

    # --- construir-deb.sh ---
    try:
        with open(ARCHIVO_DEB, "r", encoding="utf-8") as f:
            deb = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_DEB}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = deb.count(ANCLA_DEB)
    if n != 1:
        print(f"ERROR: el bloque de instalacion del icono se encontro {n} veces en {ARCHIVO_DEB} (se esperaba 1).")
        sys.exit(1)

    # --- src/main_gtk.c ---
    try:
        with open(ARCHIVO_C, "r", encoding="utf-8") as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_C}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for nombre, ancla, _ in PARCHES_C:
        n = codigo.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("¿Ya corriste agregar-fondo-dinamico.py y arreglar-fondo-dinamico-titlebar.py antes? No se cambio nada.")
            sys.exit(1)

    # Todo valido, ahora si escribimos.
    deb = deb.replace(ANCLA_DEB, NUEVO_DEB, 1)
    shutil.copy(ARCHIVO_DEB, ARCHIVO_DEB + ".bak2")
    print(f"Backup creado: {ARCHIVO_DEB}.bak2")
    with open(ARCHIVO_DEB, "w", encoding="utf-8") as f:
        f.write(deb)
    print(f"{ARCHIVO_DEB} parchado OK.")

    for _, ancla, nuevo in PARCHES_C:
        codigo = codigo.replace(ancla, nuevo, 1)
    shutil.copy(ARCHIVO_C, ARCHIVO_C + ".bak13")
    print(f"Backup creado: {ARCHIVO_C}.bak13")
    with open(ARCHIVO_C, "w", encoding="utf-8") as f:
        f.write(codigo)
    print(f"{ARCHIVO_C} parchado OK: la imagen ya reemplaza el degradado plano.")

    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")
    print("")
    print("(La primera vez que compiles el .deb con esto, construir-deb.sh tambien")
    print(" empaquetara la imagen para que se vea igual en las demas maquinas.)")


if __name__ == "__main__":
    main()
