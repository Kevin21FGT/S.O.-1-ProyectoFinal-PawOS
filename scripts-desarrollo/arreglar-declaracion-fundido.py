#!/usr/bin/env python3
"""
arreglar-declaracion-fundido.py

Hotfix de agregar-fundido-ventanas.py: mostrar_con_fundido() se
implementa mas abajo en el archivo (junto a aplicar_estilos()), pero
varios dialogos auxiliares (pedir_entero_dialog, etc.) estan definidos
ANTES en el archivo y ya la llaman -- en C hace falta un prototipo
declarado antes del primer uso. Este parche solo agrega esa
declaracion adelantada; no mueve ni borra nada de lo que ya existe.

Requisito: correr DESPUES de agregar-fundido-ventanas.py.

Uso: parado en la raiz del repo:
    python3 arreglar-declaracion-fundido.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define ID_PROCESO_DEMO 1u

/* ---------------------------------------------------------------
 * Utilidades comunes
 * --------------------------------------------------------------- */"""
NUEVO = """#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define ID_PROCESO_DEMO 1u

/* Prototipo adelantado: la implementacion completa (con el fundido de
 * opacidad) esta mas abajo, junto a aplicar_estilos(); se declara aqui
 * porque varios dialogos auxiliares de esta seccion (como
 * pedir_entero_dialog) ya la usan mas arriba en el archivo. */
static void mostrar_con_fundido(GtkWidget *ventana);

/* ---------------------------------------------------------------
 * Utilidades comunes
 * --------------------------------------------------------------- */"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if "static void mostrar_con_fundido(GtkWidget *ventana);" in contenido:
        print("Ya esta aplicado este parche (el prototipo ya existe). No se cambio nada.")
        return

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro el bloque esperado al inicio del archivo.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak13")
    print(f"Backup creado: {ARCHIVO}.bak13")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: prototipo de mostrar_con_fundido() agregado.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
