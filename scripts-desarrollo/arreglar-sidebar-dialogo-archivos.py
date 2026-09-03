#!/usr/bin/env python3
"""
arreglar-sidebar-dialogo-archivos.py

El panel lateral de "favoritos" (Carpeta personal, Descargas,
Documentos, etc.) del dialogo nativo de GTK para Abrir/Guardar archivo
se quedaba con fondo blanco en modo oscuro. Es un widget con su propio
nodo/clase CSS (placessidebar / .sidebar) que no hereda el fondo de
"dialog" -- por eso el resto del dialogo si cambiaba de modo y ese
panel no. Este parche le agrega fondo y color de texto propios, igual
que ya tienen "dialog" y "entry".

Uso: parado en la raiz del repo:
    python3 arreglar-sidebar-dialogo-archivos.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA_CSS = """        "entry:focus, textview:focus {"
        "  border-color: #23924B;"
        "}\","""
NUEVO_CSS = """        "entry:focus, textview:focus {"
        "  border-color: #23924B;"
        "}"

        /* Panel lateral de "favoritos" (Carpeta personal, Descargas,
         * etc.) de los dialogos nativos de Abrir/Guardar: usa su
         * propio nodo CSS (placessidebar / .sidebar) que no hereda el
         * fondo de "dialog", por eso se quedaba blanco aunque el
         * resto del dialogo si cambiara de modo. */
        "placessidebar, .sidebar {"
        "  background-color: %s;"
        "}"
        "placessidebar row, .sidebar row {"
        "  color: %s;"
        "}\","""

ANCLA_ARGS = """        fondo_dialogo,
        fondo_dialogo, color_texto, boton_borde);"""
NUEVO_ARGS = """        fondo_dialogo,
        fondo_dialogo, color_texto, boton_borde,
        fondo_dialogo, color_texto);"""


def main():
    pares = [
        (ANCLA_CSS, NUEVO_CSS, "regla CSS del placessidebar"),
        (ANCLA_ARGS, NUEVO_ARGS, "argumentos del printf"),
    ]
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak17")
    print(f"Backup creado: {ARCHIVO}.bak17")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: panel lateral del dialogo de archivos ya sigue el modo oscuro.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
