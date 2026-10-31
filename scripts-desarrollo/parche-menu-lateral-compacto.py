#!/usr/bin/env python3
"""
parche-menu-lateral-compacto.py

Menu lateral de PawOS Refugio (src/main_gtk.c):
  - Items mas compactos (alto 40 -> 32, menos relleno y menos separacion), para
    que los 12 modulos + Cuenta quepan sin tener que hacer scroll.
  - Red de seguridad: la barra lateral va dentro de un area con scroll vertical
    que SOLO aparece si la pantalla es muy baja. Ademas la ventana ya no se
    "estira" mas alto que la pantalla (causa del espacio/corte al maximizar).

No cambia ningun permiso, boton ni logica.

Uso (parado en la raiz del repo):
    python3 parche-menu-lateral-compacto.py
    make gui && ./pawos-refugio-gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "pawos-scroll-lateral"

CAMBIOS = [
    (r"""    gtk_widget_set_size_request(barra_lateral, 260, -1);
    gtk_box_pack_start(GTK_BOX(caja_raiz), barra_lateral, FALSE, FALSE, 0);
""",
     r"""    gtk_widget_set_size_request(barra_lateral, 260, -1);
    {
        /* pawos-scroll-lateral: solo muestra barra de scroll si no cabe */
        GtkWidget *scroll_lateral = gtk_scrolled_window_new(NULL, NULL);
        gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll_lateral),
                                       GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
        gtk_scrolled_window_set_shadow_type(GTK_SCROLLED_WINDOW(scroll_lateral), GTK_SHADOW_NONE);
        gtk_container_add(GTK_CONTAINER(scroll_lateral), barra_lateral);
        gtk_box_pack_start(GTK_BOX(caja_raiz), scroll_lateral, FALSE, FALSE, 0);
    }
""", "barra lateral dentro de scroll"),
    ("gtk_widget_set_size_request(boton, -1, 40);",
     "gtk_widget_set_size_request(boton, -1, 32);", "alto de items"),
    ("gtk_widget_set_size_request(btn_actualizar, -1, 40);",
     "gtk_widget_set_size_request(btn_actualizar, -1, 32);", "alto Buscar Actualizaciones"),
    ("gtk_widget_set_size_request(btn_acerca_de, -1, 40);",
     "gtk_widget_set_size_request(btn_acerca_de, -1, 32);", "alto Acerca de"),
    ("gtk_widget_set_size_request(btn_salir, -1, 40);",
     "gtk_widget_set_size_request(btn_salir, -1, 32);", "alto Salir"),
    ("gtk_widget_set_margin_top(encabezado, primera_seccion ? 4 : 16);",
     "gtk_widget_set_margin_top(encabezado, primera_seccion ? 2 : 8);", "separacion de secciones"),
    ("gtk_widget_set_margin_bottom(lbl_version, 14);",
     "gtk_widget_set_margin_bottom(lbl_version, 6);", "margen de la version"),
    ('"  padding: 8px 10px;"',
     '"  padding: 3px 10px;"', "relleno de items (CSS)"),
    ('"  padding: 22px 16px;"',
     '"  padding: 14px 16px;"', "relleno de la barra (CSS)"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_menu_lateral")
    print(f"Backup: {ARCHIVO}.bak_menu_lateral")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
