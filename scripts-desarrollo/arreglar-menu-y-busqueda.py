#!/usr/bin/env python3
"""
arreglar-menu-y-busqueda.py

Dos arreglos mas de modo oscuro:

  1. El menu desplegable de los GtkComboBox (por ejemplo el filtro
     "Texto (*.txt)" / "PDF (*.pdf)" del dialogo de guardar, pero
     tambien CUALQUIER otro combo de la app -- rol, cliente, etc.) se
     mostraba con fondo blanco: usa su propio nodo CSS ("menu"), que
     no hereda nada de "dialog" ni "window". Se le agrega fondo y
     color de texto propios.

  2. Un intento mas para el area de resultados del buscador dentro del
     dialogo de archivos: se agrega "dialog stack" a la misma regla
     (por si el contenedor que cambia entre "explorar" y "buscar" es
     un GtkStack con fondo propio, en vez de una caja/box comun).

Uso: parado en la raiz del repo:
    python3 arreglar-menu-y-busqueda.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. Menu desplegable de los combo box
# ---------------------------------------------------------------
ANCLA_MENU = '''        /* Dialogos y campos de texto */'''
NUEVO_MENU = '''        /* Menu desplegable de los combo box (ej. el filtro
         * Texto/PDF del dialogo de guardar, o cualquier otro combo de
         * la app): tiene su propio nodo CSS, no hereda nada de
         * "dialog" ni "window". */
        "menu, .menu {"
        "  background-color: %s;"
        "  color: %s;"
        "}"
        "menuitem {"
        "  color: %s;"
        "}"

        /* Dialogos y campos de texto */'''

# ---------------------------------------------------------------
# 2. Un intento mas para el area de busqueda (agregar "dialog stack")
# ---------------------------------------------------------------
ANCLA_STACK = '''        "dialog scrolledwindow, dialog viewport, dialog list {"'''
NUEVO_STACK = '''        "dialog scrolledwindow, dialog viewport, dialog list, dialog stack {"'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA_MENU) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque del menu.")
        print("       No se cambio nada.")
        sys.exit(1)
    if contenido.count(ANCLA_STACK) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque del stack.")
        print("       Puede que arreglar-busqueda-dialogo-archivos.py no se haya aplicado todavia.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA_MENU, NUEVO_MENU, 1)
    contenido = contenido.replace(ANCLA_STACK, NUEVO_STACK, 1)

    # Los 3 nuevos %s del menu necesitan 3 argumentos nuevos, al final
    # de la lista del printf.
    ANCLA_ARGS = "fondo_dialogo, color_texto, boton_borde,\n        fondo_dialogo, color_texto);"
    NUEVO_ARGS = "fondo_dialogo, color_texto, boton_borde,\n        fondo_dialogo, color_texto,\n        fondo_dialogo, color_texto, color_texto);"
    if contenido.count(ANCLA_ARGS) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la lista de argumentos.")
        print("       No se cambio nada.")
        sys.exit(1)
    contenido = contenido.replace(ANCLA_ARGS, NUEVO_ARGS, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak20")
    print(f"Backup creado: {ARCHIVO}.bak20")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: menu de combo box + otro intento del area de busqueda.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
