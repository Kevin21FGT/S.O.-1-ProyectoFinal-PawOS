#!/usr/bin/env python3
"""
arreglar-busqueda-dialogo-archivos.py

Tercera pasada del arreglo del dialogo nativo de Abrir/Guardar: el
panel lateral y la barra de ruta ya quedaron oscuros, pero el area de
resultados al usar el buscador (icono de lupa) sigue blanca -- esa
zona vive dentro de un GtkScrolledWindow/GtkViewport que por defecto
tiene su propio fondo opaco (no hereda el de "dialog").

Igual que las dos pasadas anteriores: se agregan mas selectores a la
misma regla, sin variables nuevas. Los selectores que no existan en
este tema simplemente no hacen nada.

Requisito: correr DESPUES de arreglar-barra-ruta-dialogo-archivos.py.

Uso: parado en la raiz del repo:
    python3 arreglar-busqueda-dialogo-archivos.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        "dialog, dialog box, pathbar, .path-bar, placesview {"
        "  background-color: %s;"
        "}"'''
NUEVO = '''        "dialog, dialog box, pathbar, .path-bar, placesview,"
        "dialog scrolledwindow, dialog viewport, dialog list {"
        "  background-color: %s;"
        "}"'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque esperado se encontro {n} veces (se esperaba 1). No se cambio nada.")
        print("       Puede que arreglar-barra-ruta-dialogo-archivos.py no se haya aplicado todavia.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak19")
    print(f"Backup creado: {ARCHIVO}.bak19")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: area de resultados de busqueda cubierta.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
