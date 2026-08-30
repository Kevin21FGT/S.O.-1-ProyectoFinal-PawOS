#!/usr/bin/env python3
"""
excluir-merges-novedades.py

Corrige el changelog del dialogo de novedades (boton "Buscar
Actualizaciones") para que NO muestre los commits de tipo "Merge branch..."
/ "Merge pull request #..." -- esas lineas son ruido de git, no cambios
reales para el usuario final.

Agrega --no-merges al git log que arma la lista.

Uso: parado en la raiz del repo (rama con el dialogo de novedades ya
aplicado, por ejemplo rama-Kevin):
    python3 excluir-merges-novedades.py

Hace backup automatico a src/main_gtk.c.bak2 antes de tocar nada, y
aborta sin cambiar nada si no encuentra el texto exacto esperado (por
ejemplo si el archivo ya fue corregido antes).
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''"  else echo HAY_CAMBIOS; git log \\"$LOCAL..$REMOTE\\" --pretty=format:%s; fi; "'''
NUEVO = '''"  else echo HAY_CAMBIOS; git log \\"$LOCAL..$REMOTE\\" --no-merges --pretty=format:%s; fi; "'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la linea exacta")
        print("       del git log esperada. Puede que ya haya sido corregida antes,")
        print("       o que el archivo este distinto a lo esperado. No se cambio nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak2")
    print(f"Backup creado: {ARCHIVO}.bak2")

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} corregido OK: los commits de merge ya no apareceran en el changelog.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
