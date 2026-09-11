#!/usr/bin/env python3
"""
arreglar-barra-ruta-dialogo-archivos.py

Segunda pasada del arreglo del dialogo nativo de Abrir/Guardar: el
panel lateral ya quedo oscuro (arreglar-sidebar-dialogo-archivos.py),
pero la barra de arriba (flechas atras/adelante, boton de "carpeta
personal", buscar, nueva carpeta -- el "pathbar") sigue blanca. Es
otro widget con su propio nodo CSS (pathbar / .path-bar) que tampoco
hereda el fondo de "dialog".

En vez de adivinar un solo nombre exacto, esta regla cubre varios
nombres/clases que GTK3 usa en distintas versiones para estos
contenedores internos del selector de archivos -- los que no existen
en el tema de este sistema simplemente no hacen nada (CSS invalido de
selector no rompe nada en GTK, solo no aplica).

No agrega variables nuevas: reutiliza el mismo color que ya tenia
"dialog { background-color: %s; }", asi que no hay que tocar la lista
de argumentos del printf.

Requisito: correr DESPUES de arreglar-sidebar-dialogo-archivos.py.

Uso: parado en la raiz del repo:
    python3 arreglar-barra-ruta-dialogo-archivos.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        /* Dialogos y campos de texto */
        "dialog { background-color: %s; }"'''
NUEVO = '''        /* Dialogos y campos de texto */
        "dialog, dialog box, pathbar, .path-bar, placesview {"
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
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak18")
    print(f"Backup creado: {ARCHIVO}.bak18")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: barra de ruta del dialogo de archivos cubierta.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
