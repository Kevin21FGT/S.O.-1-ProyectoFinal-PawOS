#!/usr/bin/env python3
"""
arreglar-barra-titulo.py

La barra de titulo de las ventanas/dialogos (donde sale "PawOS Refugio"
y la X de cerrar) se queda blanca en modo oscuro. Como el programa no
define una barra de titulo propia, GTK genera una automatica usando
los nodos CSS "headerbar" / "decoration" / ".titlebar" -- que la hoja
de estilos nunca tocaba (solo "window" y "dialog"). Este parche le
agrega color de fondo/texto tambien a esos nodos.

Requisito: correr DESPUES de arreglar-contraste-botones-v2.py.

Uso: parado en la raiz del repo:
    python3 arreglar-barra-titulo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """        /* Fondo general de la app */
        "window { background-color: %s; }"
        "label { color: %s; }\""""
NUEVO = """        /* Fondo general de la app */
        "window { background-color: %s; }"
        "label { color: %s; }"

        /* Barra de titulo automatica de GTK (no hay una propia
         * definida): sin esto se queda blanca aunque todo lo demas
         * cambie de modo. */
        "headerbar, .titlebar, decoration {"
        "  background-color: %s;"
        "  background-image: none;"
        "  color: %s;"
        "}"
        "headerbar button, .titlebar button, decoration button {"
        "  background-color: %s;"
        "  background-image: none;"
        "  color: %s;"
        "}\""""

ANCLA_ARGS = """        fondo_ventana, color_texto,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,"""
NUEVO_ARGS = """        fondo_ventana, color_texto,
        fondo_ventana, color_texto,
        boton_bg, boton_fg,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,"""


def main():
    pares = [
        (ANCLA, NUEVO, "regla CSS de la barra de titulo"),
        (ANCLA_ARGS, NUEVO_ARGS, "argumentos del printf"),
    ]
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       Puede que arreglar-contraste-botones-v2.py no se haya aplicado")
            print("       todavia. No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak9")
    print(f"Backup creado: {ARCHIVO}.bak9")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
