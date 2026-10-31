#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-cursor-carga-mascotas.py

Agrega un cursor de "cargando" (reloj de arena) mientras la pantalla
de Gestion de Mascotas espera la respuesta de mascota_listar() contra
el SQL Server remoto. No reduce el tiempo real de espera (eso es
latencia de red hacia el servidor gratuito de SmarterASP), pero evita
que la ventana se sienta "congelada" sin ninguna señal de que esta
trabajando.

No cambia ninguna logica de negocio: el mensaje de error y el llenado
de la lista quedan exactamente iguales, solo se le agrega el cursor
alrededor de la llamada bloqueante.

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-cursor-carga-mascotas.py
"""
import shutil
import sys
from pathlib import Path

MAIN_GTK_C = Path("src/main_gtk.c")

ANCLA = """static void cargar_mascotas(ContextoMascotas *ctx) {
    gtk_list_store_clear(ctx->store);

    Mascota *ms;
    int n;
    if (mascota_listar(&ms, &n) != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de mascotas.", TRUE);
        return;
    }"""

NUEVO = """static void cargar_mascotas(ContextoMascotas *ctx) {
    gtk_list_store_clear(ctx->store);

    /* Cursor de "cargando" mientras espera la respuesta del SQL Server
     * remoto, para que la pantalla no se sienta congelada. */
    GdkWindow *gdkwin_carga = gtk_widget_get_window(ctx->ventana);
    GdkCursor *cursor_reloj = NULL;
    if (gdkwin_carga) {
        cursor_reloj = gdk_cursor_new_for_display(gdk_display_get_default(), GDK_WATCH);
        gdk_window_set_cursor(gdkwin_carga, cursor_reloj);
        while (gtk_events_pending()) gtk_main_iteration();
    }

    Mascota *ms;
    int n;
    int rc_listar = mascota_listar(&ms, &n);

    if (gdkwin_carga) {
        gdk_window_set_cursor(gdkwin_carga, NULL);
        if (cursor_reloj) g_object_unref(cursor_reloj);
    }

    if (rc_listar != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo leer la lista de mascotas.", TRUE);
        return;
    }"""


def main():
    if not MAIN_GTK_C.exists():
        print(f"ERROR: no se encontro {MAIN_GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = MAIN_GTK_C.read_text(encoding="utf-8")

    apariciones = contenido.count(ANCLA)
    if apariciones == 0:
        print("ERROR: no se encontro el ancla de cargar_mascotas() en src/main_gtk.c.")
        print("       (puede que ya este parchado, o el codigo cambio)")
        sys.exit(1)
    if apariciones > 1:
        print("ERROR: el ancla aparece mas de una vez, no es seguro parchar automaticamente.")
        sys.exit(1)

    backup = MAIN_GTK_C.with_suffix(".c.bak_cursor_carga")
    shutil.copy(MAIN_GTK_C, backup)

    contenido = contenido.replace(ANCLA, NUEVO, 1)
    MAIN_GTK_C.write_text(contenido, encoding="utf-8")

    print(f"  {MAIN_GTK_C}: cargar_mascotas() ahora muestra un cursor de carga mientras espera al servidor.")
    print(f"  Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  1. make gui")
    print("  2. Abre Gestion de Mascotas y observa si el cursor cambia a un reloj")
    print("     de arena mientras carga la lista.")


if __name__ == "__main__":
    main()
