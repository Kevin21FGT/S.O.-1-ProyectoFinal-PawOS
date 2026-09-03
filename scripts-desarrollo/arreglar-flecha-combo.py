#!/usr/bin/env python3
"""
arreglar-flecha-combo.py

Ultimo detalle del filtro Texto/PDF (y de cualquier otro GtkComboBox
de la app): el boton que abre el desplegable (con la flechita) usa su
propio nodo CSS ("combobox"), separado del "button" generico que ya
esta cubierto -- por eso se quedaba con un borde/esquina blanca. Se le
agrega el mismo tratamiento (fondo, color, sin imagen de fondo) que ya
tiene "button".

Uso: parado en la raiz del repo:
    python3 arreglar-flecha-combo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        /* Menu desplegable de los combo box (ej. el filtro
         * Texto/PDF del dialogo de guardar, o cualquier otro combo de
         * la app): tiene su propio nodo CSS, no hereda nada de
         * "dialog" ni "window". */
        "menu, .menu {"
        "  background-color: %s;"
        "  color: %s;"
        "}"
        "menuitem {"
        "  color: %s;"
        "}"'''
NUEVO = '''        /* Menu desplegable de los combo box (ej. el filtro
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

        /* El boton que abre ese desplegable (con la flechita): tiene
         * su propio nodo CSS ("combobox"), separado del "button"
         * generico -- por eso se quedaba con una esquina blanca. */
        "combobox, combobox button, combobox arrow {"
        "  background-color: %s;"
        "  background-image: none;"
        "  color: %s;"
        "}"'''

ANCLA_ARGS = "fondo_dialogo, color_texto,\n        fondo_dialogo, color_texto, color_texto);"
NUEVO_ARGS = "fondo_dialogo, color_texto,\n        fondo_dialogo, color_texto, color_texto,\n        boton_bg, boton_fg);"


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque del menu.")
        print("       Puede que arreglar-menu-y-busqueda.py no se haya aplicado todavia.")
        print("       No se cambio nada.")
        sys.exit(1)
    if contenido.count(ANCLA_ARGS) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la lista de argumentos.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)
    contenido = contenido.replace(ANCLA_ARGS, NUEVO_ARGS, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak21")
    print(f"Backup creado: {ARCHIVO}.bak21")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: boton del combo box cubierto.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
