#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quita los g_print("[DIAG] ...") de diagnostico agregados por
diagnostico-maximizar.py, ahora que ya confirmamos que el boton de
maximizar funciona correctamente (el problema real era la resolucion
de pantalla de la VM, no el codigo). Deja la funcion tal como estaba
antes del diagnostico.
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA = r'''static void on_click_maximizar_restaurar(GtkButton *boton, gpointer datos) {
    g_print("[DIAG] clic en boton maximizar/restaurar, datos=%p\n", datos);
    GtkWindow *ventana = GTK_WINDOW(datos);

    gint ancho_ventana = 0, alto_ventana = 0;
    gtk_window_get_size(ventana, &ancho_ventana, &alto_ventana);
    g_print("[DIAG] gtk_window_get_size -> ancho=%d alto=%d\n", ancho_ventana, alto_ventana);

    GdkWindow *ventana_gdk = gtk_widget_get_window(GTK_WIDGET(ventana));
    g_print("[DIAG] gtk_widget_get_window -> %p\n", (void *)ventana_gdk);
    GdkMonitor *monitor = gdk_display_get_monitor_at_window(gdk_display_get_default(), ventana_gdk);
    g_print("[DIAG] monitor -> %p\n", (void *)monitor);
    GdkRectangle area_monitor = {0, 0, 0, 0};
    gdk_monitor_get_geometry(monitor, &area_monitor);
    g_print("[DIAG] area_monitor -> x=%d y=%d ancho=%d alto=%d\n",
        area_monitor.x, area_monitor.y, area_monitor.width, area_monitor.height);

    gboolean parece_maximizada =
        ancho_ventana >= area_monitor.width - 4 &&
        alto_ventana >= area_monitor.height - 4;
    g_print("[DIAG] parece_maximizada -> %s\n", parece_maximizada ? "TRUE (va a des-maximizar)" : "FALSE (va a maximizar)");

    GtkWidget *imagen;
    if (parece_maximizada) {
        gtk_window_unmaximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-maximize-symbolic", GTK_ICON_SIZE_BUTTON);
    } else {
        gtk_window_maximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON);
    }
    gtk_button_set_image(GTK_BUTTON(boton), imagen);
    g_print("[DIAG] fin del clic\n");
}'''

NUEVO = r'''static void on_click_maximizar_restaurar(GtkButton *boton, gpointer datos) {
    GtkWindow *ventana = GTK_WINDOW(datos);

    gint ancho_ventana = 0, alto_ventana = 0;
    gtk_window_get_size(ventana, &ancho_ventana, &alto_ventana);

    GdkWindow *ventana_gdk = gtk_widget_get_window(GTK_WIDGET(ventana));
    GdkMonitor *monitor = gdk_display_get_monitor_at_window(gdk_display_get_default(), ventana_gdk);
    GdkRectangle area_monitor;
    gdk_monitor_get_geometry(monitor, &area_monitor);

    gboolean parece_maximizada =
        ancho_ventana >= area_monitor.width - 4 &&
        alto_ventana >= area_monitor.height - 4;

    GtkWidget *imagen;
    if (parece_maximizada) {
        gtk_window_unmaximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-maximize-symbolic", GTK_ICON_SIZE_BUTTON);
    } else {
        gtk_window_maximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON);
    }
    gtk_button_set_image(GTK_BUTTON(boton), imagen);
}'''


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
    print("Se quitaron los mensajes [DIAG] de diagnostico.")


if __name__ == "__main__":
    main()
