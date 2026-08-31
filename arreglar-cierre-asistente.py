#!/usr/bin/env python3
"""
arreglar-cierre-asistente.py

Bug: en el asistente de bienvenida, si le dabas clic a la X de la
ventana "Crear Administrador" en vez de completar el formulario, el
programa simplemente volvia a abrir la misma ventana en un ciclo
infinito -- no habia forma de cerrar el programa desde ahi.

Fix: cerrar la ventana (X) o cualquier respuesta que no sea "Crear
cuenta" ahora SI cierra el programa por completo (como cancelar un
instalador). Ya no hace falta de todas formas para "saltarse" la
creacion del Administrador -- solo cambia que ahora se puede salir.

Requisito: correr DESPUES de agregar-asistente-bienvenida.py.

Uso: parado en la raiz del repo:
    python3 arreglar-cierre-asistente.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """        if (respuesta != GTK_RESPONSE_ACCEPT) {
            gtk_widget_destroy(dialogo);
            continue;
        }"""
NUEVO = """        if (respuesta != GTK_RESPONSE_ACCEPT) {
            /* Cerrar esta ventana (la X) o cancelar aqui cierra el
             * programa por completo -- antes esto volvia a abrir la
             * misma ventana en un ciclo infinito, sin forma de salir. */
            gtk_widget_destroy(dialogo);
            db_close();
            exit(0);
        }"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque esperado.")
        print("       Puede que agregar-asistente-bienvenida.py no se haya aplicado todavia,")
        print("       o que el archivo ya haya sido modificado. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak10")
    print(f"Backup creado: {ARCHIVO}.bak10")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora:  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
