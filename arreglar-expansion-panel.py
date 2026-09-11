#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arregla que el contenido embebido en el panel (tabla de Gestion de
Mascotas, tarjeta de bienvenida) no se expandia para llenar el espacio
disponible -- se quedaba pegado arriba con un espacio vacio enorme
debajo y la tabla con scroll cortado.

Causa: mostrar_en_panel() y el llenado inicial del area_dinamica usaban
gtk_container_add(), que en un GtkBox equivale a empaquetar con
expand=FALSE, fill=FALSE. Se cambia a gtk_box_pack_start(...,
TRUE, TRUE, 0) para que el contenido crezca y llene el panel.

No toca ninguna logica de datos ni de botones.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA_1 = r'''    g_list_free(hijos);
    gtk_container_add(GTK_CONTAINER(contenedor), nuevo);
    gtk_widget_show_all(nuevo);
}'''

NUEVO_1 = r'''    g_list_free(hijos);
    gtk_box_pack_start(GTK_BOX(contenedor), nuevo, TRUE, TRUE, 0);
    gtk_widget_show_all(nuevo);
}'''

ANCLA_2 = r'''    gtk_box_pack_start(GTK_BOX(panel_contenido), area_dinamica, TRUE, TRUE, 0);
    gtk_container_add(GTK_CONTAINER(area_dinamica), construir_tarjeta_bienvenida());
    datos_botones->area_dinamica = area_dinamica;'''

NUEVO_2 = r'''    gtk_box_pack_start(GTK_BOX(panel_contenido), area_dinamica, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(area_dinamica), construir_tarjeta_bienvenida(), TRUE, TRUE, 0);
    datos_botones->area_dinamica = area_dinamica;'''


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

    for nombre, ancla in (("ANCLA_1", ANCLA_1), ("ANCLA_2", ANCLA_2)):
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: {nombre} aparece {n} veces (se esperaba 1). No se modifico nada.")
            sys.exit(1)

    nuevo_contenido = contenido.replace(ANCLA_1, NUEVO_1).replace(ANCLA_2, NUEVO_2)

    respaldo = siguiente_backup(ARCHIVO)
    shutil.copy(ARCHIVO, respaldo)
    ARCHIVO.write_text(nuevo_contenido, encoding="utf-8")

    print(f"Listo. Respaldo guardado en {respaldo}")
    print("Cambios aplicados:")
    print("  - El contenido del panel (tabla, tarjeta de bienvenida) ahora se expande para llenar el espacio")


if __name__ == "__main__":
    main()
