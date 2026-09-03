#!/usr/bin/env python3
"""
arreglar-contraste-botones-v2.py

Segundo intento del arreglo de contraste de botones. La primera pasada
(arreglar-contraste-botones.py) le puso background-color propio a
"button {}", pero el tema de GNOME probablemente pinta los botones con
un degradado (background-image), que es una propiedad CSS DISTINTA de
background-color -- como no la tocabamos, el degradado del tema se
quedaba encima tapando nuestro color plano. Este parche agrega
"background-image: none;" para forzar el color plano.

Requisito: correr DESPUES de arreglar-contraste-botones.py (usa el
bloque que ese script dejo como ancla).

Uso: parado en la raiz del repo:
    python3 arreglar-contraste-botones-v2.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """        "button {"
        "  padding: 10px;"
        "  border-radius: 10px;"
        "  transition: 150ms ease-in-out;"
        "  background-color: %s;"
        "  color: %s;"
        "  border: 1px solid %s;"
        "}\""""
NUEVO = """        "button {"
        "  padding: 10px;"
        "  border-radius: 10px;"
        "  transition: 150ms ease-in-out;"
        "  background-color: %s;"
        "  background-image: none;"
        "  color: %s;"
        "  border: 1px solid %s;"
        "}\""""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque esperado.")
        print("       Puede que arreglar-contraste-botones.py no se haya aplicado todavia.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak8")
    print(f"Backup creado: {ARCHIVO}.bak8")
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
