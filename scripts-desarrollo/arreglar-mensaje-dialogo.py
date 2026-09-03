#!/usr/bin/env python3
"""
arreglar-mensaje-dialogo.py

Los dialogos simples tipo "Ya tienes la ultima version instalada",
"Mascota registrada correctamente", etc. (los que usa mostrar_mensaje(),
gtk_message_dialog_new()) se quedaban con el area del mensaje en
blanco -- es un GtkMessageDialog, con una estructura interna distinta
a los dialogos normales (gtk_dialog_new_with_buttons), que usan
selectores CSS propios.

Uso: parado en la raiz del repo:
    python3 arreglar-mensaje-dialogo.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = '''        "dialog, dialog box, pathbar, .path-bar, placesview,"
        "dialog scrolledwindow, dialog viewport, dialog list, dialog stack {"
        "  background-color: %s;"
        "}"'''
NUEVO = '''        "dialog, dialog box, pathbar, .path-bar, placesview,"
        "dialog scrolledwindow, dialog viewport, dialog list, dialog stack,"
        "messagedialog, messagedialog box, .message-area, .message-area box {"
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak24")
    print(f"Backup creado: {ARCHIVO}.bak24")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: dialogos de mensaje simple (GtkMessageDialog) cubiertos.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
