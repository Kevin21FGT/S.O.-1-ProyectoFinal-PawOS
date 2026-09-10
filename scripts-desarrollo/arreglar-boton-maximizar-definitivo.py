#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arregla el boton de maximizar/restaurar de forma definitiva.

Causa raiz: on_click_maximizar_restaurar() decidia que hacer llamando a
gtk_window_is_maximized() justo en el momento del clic. Esa funcion
refleja el ULTIMO ESTADO CONFIRMADO por el gestor de ventanas, que
llega de forma asincrona -- si el usuario agrando la ventana a mano
(arrastrando una esquina) o el gestor de ventanas tardo en confirmar un
cambio anterior, el boton quedaba "confundido": a veces no hacia nada,
a veces hacia lo contrario de lo esperado.

Arreglo: seguir el estado real por la señal "window-state-event" (que
GTK dispara cuando el gestor de ventanas YA confirmo el cambio), guardar
ese estado en la propia ventana, y que el boton de clic solo consulte
ese estado guardado -- nunca gtk_window_is_maximized() en el momento
del clic. Asi el boton siempre hace lo correcto sin importar si la
ventana se agrando con el boton, arrastrando, o por cualquier otro
medio.

Aplica tanto a la ventana del menu principal como al selector de
entrada, porque ambos comparten la misma funcion
agregar_barra_titulo_con_maximizar().
"""
import shutil
import sys
from pathlib import Path

ARCHIVO = Path("src/main_gtk.c")

ANCLA = r'''static void on_click_maximizar_restaurar(GtkButton *boton, gpointer datos) {
    GtkWindow *ventana = GTK_WINDOW(datos);
    GtkWidget *imagen;
    if (gtk_window_is_maximized(ventana)) {
        gtk_window_unmaximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-maximize-symbolic", GTK_ICON_SIZE_BUTTON);
    } else {
        gtk_window_maximize(ventana);
        imagen = gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON);
    }
    gtk_button_set_image(GTK_BUTTON(boton), imagen);
}

static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo) {
    GtkWidget *barra = gtk_header_bar_new();
    gtk_header_bar_set_title(GTK_HEADER_BAR(barra), titulo);

    GtkWidget *boton_maximizar = gtk_button_new();
    gtk_button_set_image(GTK_BUTTON(boton_maximizar),
        gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON));
    gtk_widget_set_tooltip_text(boton_maximizar, "Maximizar / Restaurar");
    g_signal_connect(boton_maximizar, "clicked", G_CALLBACK(on_click_maximizar_restaurar), ventana);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(barra), boton_maximizar);'''

NUEVO = r'''static void on_estado_ventana_cambio(GtkWidget *ventana, GdkEventWindowState *evento, gpointer datos) {
    GtkWidget *boton = GTK_WIDGET(datos);
    gboolean maximizada = (evento->new_window_state & GDK_WINDOW_STATE_MAXIMIZED) != 0;
    GtkWidget *imagen = gtk_image_new_from_icon_name(
        maximizada ? "window-restore-symbolic" : "window-maximize-symbolic",
        GTK_ICON_SIZE_BUTTON);
    gtk_button_set_image(GTK_BUTTON(boton), imagen);
    /* Guardamos el estado confirmado en la propia ventana -- el clic
     * del boton solo lee este valor, nunca pregunta el estado en vivo. */
    g_object_set_data(G_OBJECT(ventana), "pawos-maximizada", GINT_TO_POINTER(maximizada));
}

/* El clic ya no le pregunta a GTK si esta maximizada en ese instante
 * (eso puede estar desincronizado con el gestor de ventanas). Solo lee
 * el ultimo estado CONFIRMADO, guardado por on_estado_ventana_cambio()
 * cuando el gestor de ventanas realmente aplico el cambio. */
static void on_click_maximizar_restaurar(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWindow *ventana = GTK_WINDOW(datos);
    gboolean maximizada = GPOINTER_TO_INT(g_object_get_data(G_OBJECT(ventana), "pawos-maximizada"));
    if (maximizada) {
        gtk_window_unmaximize(ventana);
    } else {
        gtk_window_maximize(ventana);
    }
}

static GtkWidget *agregar_barra_titulo_con_maximizar(GtkWindow *ventana, const char *titulo) {
    GtkWidget *barra = gtk_header_bar_new();
    gtk_header_bar_set_title(GTK_HEADER_BAR(barra), titulo);

    GtkWidget *boton_maximizar = gtk_button_new();
    gtk_button_set_image(GTK_BUTTON(boton_maximizar),
        gtk_image_new_from_icon_name("window-restore-symbolic", GTK_ICON_SIZE_BUTTON));
    gtk_widget_set_tooltip_text(boton_maximizar, "Maximizar / Restaurar");
    g_signal_connect(boton_maximizar, "clicked", G_CALLBACK(on_click_maximizar_restaurar), ventana);
    g_signal_connect(ventana, "window-state-event", G_CALLBACK(on_estado_ventana_cambio), boton_maximizar);
    gtk_header_bar_pack_end(GTK_HEADER_BAR(barra), boton_maximizar);'''


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
    print("  - El boton de maximizar/restaurar ahora sigue el estado confirmado por el gestor de ventanas")
    print("  - Aplica tanto al menu principal como al selector de entrada")


if __name__ == "__main__":
    main()
