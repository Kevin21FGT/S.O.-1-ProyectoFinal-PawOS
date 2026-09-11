#!/usr/bin/env python3
"""
agregar-spinner-buscando.py

Le agrega un GtkSpinner (icono animado de "cargando") al dialogo
"Buscando actualizaciones..." que ya se muestra a la fuerza justo
antes de la operacion bloqueante (git fetch). No cambia el flujo ni la
logica: sigue siendo el mismo dialogo, mostrado igual, destruido igual
-- solo se le agrega el spinner adentro para que se vea menos como que
la app se "congelo" un momento.

Uso: parado en la raiz del repo:
    python3 agregar-spinner-buscando.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """    GtkWidget *dialogo_buscando = gtk_message_dialog_new(
        padre, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_NONE,
        "Buscando actualizaciones...");
    gtk_widget_show_all(dialogo_buscando);
    while (gtk_events_pending()) gtk_main_iteration();"""
NUEVO = """    GtkWidget *dialogo_buscando = gtk_message_dialog_new(
        padre, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_NONE,
        "Buscando actualizaciones...");
    GtkWidget *spinner_buscando = gtk_spinner_new();
    gtk_spinner_start(GTK_SPINNER(spinner_buscando));
    gtk_box_pack_start(
        GTK_BOX(gtk_message_dialog_get_message_area(GTK_MESSAGE_DIALOG(dialogo_buscando))),
        spinner_buscando, FALSE, FALSE, 6);
    gtk_widget_show_all(dialogo_buscando);
    while (gtk_events_pending()) gtk_main_iteration();"""


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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak16")
    print(f"Backup creado: {ARCHIVO}.bak16")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: spinner agregado al dialogo de 'Buscando actualizaciones'.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
