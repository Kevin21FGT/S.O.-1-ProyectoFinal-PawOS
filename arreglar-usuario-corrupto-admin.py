#!/usr/bin/env python3
"""
arreglar-usuario-corrupto-admin.py

Bug real y antiguo (ya estaba desde ocultar-acceso-admin.py, antes de
esta sesion): en el acceso oculto del Administrador (dentro del
formulario de "Soy Cliente"), el codigo llamaba gtk_widget_destroy()
sobre el dialogo ANTES de copiar el texto escrito en el campo de
correo. Como GTK libera el widget de la caja de texto al destruir el
dialogo, "correo_ingresado" (que apunta al buffer interno del
GtkEntry) queda apuntando a memoria ya liberada -- leerlo despues (en
el snprintf) es un use-after-free clasico. Antes casi nunca se notaba
(la memoria liberada a veces todavia tenia el texto viejo por pura
suerte), pero con las pantallas nuevas que agregamos hoy (que reservan
y liberan mas memoria) empezo a corromperse de verdad, mostrando
caracteres invalidos en el "Bienvenido, ...".

Fix: copiar el texto ANTES de destruir el dialogo -- simplemente se
invierte el orden de esas dos lineas.

Uso: parado en la raiz del repo:
    python3 arreglar-usuario-corrupto-admin.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """            && rol_secreto == ROL_ADMIN) {
            gtk_widget_destroy(dialogo);
            snprintf(cliente_out->nombre, sizeof(cliente_out->nombre), "%s", correo_ingresado);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
        }"""
NUEVO = """            && rol_secreto == ROL_ADMIN) {
            /* Copiar el texto ANTES de destruir el dialogo: una vez
             * destruido, "correo_ingresado" (que apunta al buffer
             * interno del GtkEntry) queda invalido -- leerlo despues
             * es memoria ya liberada (use-after-free). */
            snprintf(cliente_out->nombre, sizeof(cliente_out->nombre), "%s", correo_ingresado);
            gtk_widget_destroy(dialogo);
            if (es_admin_out) *es_admin_out = TRUE;
            return TRUE;
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
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak14")
    print(f"Backup creado: {ARCHIVO}.bak14")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora:  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
