#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Causa raiz real del boton de maximizar/restaurar que nunca funcionaba en
la ventana principal: el propio gestor de ventanas (GNOME/mutter) tenia
la opcion "Maximizar" DESHABILITADA para esa ventana (confirmado viendo
el menu de clic derecho sobre la barra de titulo -- "Maximizar" salia en
gris, no disponible). Esto no tiene nada que ver con nuestro codigo del
boton ni con la VM en general: el dialogo selector de entrada (la
pantalla de "Soy Colaborador" / "Soy Cliente") YA tenia el arreglo para
este mismo problema, documentado en su propio comentario:

    /* Sin esto el gestor de ventanas trata el dialogo como una ventana
     * simple y no muestra el boton de maximizar/restaurar. */
    gtk_window_set_type_hint(GTK_WINDOW(dialogo), GDK_WINDOW_TYPE_HINT_NORMAL);

Ese arreglo nunca se aplico a la ventana principal del menu
(construir_ventana_principal), que es justo donde Kevin reportaba el
bug. Se agrega la misma linea aqui.

No toca layout, CSS, ni ninguna logica de negocio -- solo un hint que
le indica al gestor de ventanas que esta ventana se comporta como una
ventana normal (maximizable), igual que ya se hizo con el selector.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA = r'''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 900, 700);
    gtk_window_set_resizable(GTK_WINDOW(ventana), TRUE);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 0);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);'''

NUEVO = r'''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 900, 700);
    gtk_window_set_resizable(GTK_WINDOW(ventana), TRUE);
    /* Sin esto el gestor de ventanas puede dejar deshabilitada la
     * opcion de maximizar para esta ventana (mismo problema que ya se
     * habia resuelto antes en el dialogo selector de entrada). */
    gtk_window_set_type_hint(GTK_WINDOW(ventana), GDK_WINDOW_TYPE_HINT_NORMAL);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 0);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);'''


def siguiente_backup(ruta: Path) -> Path:
    n = 1
    while True:
        candidato = ruta.with_name(ruta.name + f".bak{n}")
        if not candidato.exists():
            return candidato
        n += 1


def main():
    if not ARCHIVO.exists():
        print(f"ERROR: no se encontro {ARCHIVO}. Ejecuta este script desde la raiz del repo.")
        sys.exit(1)

    contenido = ARCHIVO.read_text(encoding="utf-8")

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el ancla aparece {n} veces (se esperaba 1). No se modifico nada.")
        sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA, NUEVO)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Cambios aplicados:")
    print("  - La ventana principal ahora fuerza GDK_WINDOW_TYPE_HINT_NORMAL")
    print("  - Esto deberia habilitar 'Maximizar' en el menu del gestor de ventanas")


if __name__ == "__main__":
    main()
