#!/usr/bin/env python3
import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.15"'
NUEVO = '#define PAWOS_VERSION "1.16"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro la version 1.15 esperada en version.h. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak9")
    print(f"Backup creado: {ARCHIVO}.bak9")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.15 -> 1.16.")


if __name__ == "__main__":
    main()
