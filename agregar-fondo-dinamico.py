#!/usr/bin/env python3
"""
agregar-fondo-dinamico.py

Rediseno visual: agrega un fondo con degradado verde ("dinamico", igual
para modo claro y oscuro, como el banner) a las 4 pantallas de entrada:

  1. Selector inicial (Soy Colaborador / Soy Cliente)   -> pantalla completa
  2. Login de clientes (Acceso de Clientes)
  3. Registro de clientes (Crear cuenta)
  4. Menu principal (despues de iniciar sesion)          -> pantalla completa

NO se toca ninguna logica: solo se agrega una clase de estilo CSS a un
contenedor que ya existe, y (solo en las pantallas 1 y 4) una llamada a
gtk_window_maximize() para que abran en pantalla completa -- conservando
los botones de maximizar/restaurar/cerrar de la ventana, GTK los sigue
mostrando normalmente al maximizar (no es lo mismo que fullscreen()).

Uso: parado en la raiz del repo:
    python3 agregar-fondo-dinamico.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------------------
# Parche 1: nueva clase CSS ".pawos-fondo-dinamico" dentro de aplicar_estilos()
# ---------------------------------------------------------------------------
ANCLA_CSS = '''        ".encabezado-banner label { color: #FFFFFF; }"
        ".subtitulo-banner { color: #D9F2E0; }"
'''
NUEVO_CSS = '''        ".encabezado-banner label { color: #FFFFFF; }"
        ".subtitulo-banner { color: #D9F2E0; }"

        /* Fondo dinamico para las pantallas de bienvenida: selector inicial,
         * login/registro de clientes y menu principal. Un solo color de marca
         * (no cambia con modo claro/oscuro, igual que el banner). */
        "dialog.pawos-fondo-dinamico, dialog.pawos-fondo-dinamico box,"
        ".pawos-fondo-dinamico {"
        "  background-image: linear-gradient(160deg, #0E3D1E 0%%, #16632F 35%%, #23924B 68%%, #3FBE79 100%%);"
        "}"
        ".pawos-fondo-dinamico label { color: #FFFFFF; }"
        ".pawos-fondo-dinamico entry, .pawos-fondo-dinamico textview,"
        ".pawos-fondo-dinamico textview text {"
        "  background-color: rgba(255,255,255,0.94);"
        "  color: #14301D;"
        "}"
'''

# ---------------------------------------------------------------------------
# Parche 2: menu principal (construir_ventana_principal) -> fondo + maximizar
# ---------------------------------------------------------------------------
ANCLA_MENU = '''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 580, 660);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);
'''
NUEVO_MENU = '''static void construir_ventana_principal(Rol rol, const char *usuario) {
    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "PawOS Refugio");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 580, 660);
    gtk_window_set_position(GTK_WINDOW(ventana), GTK_WIN_POS_CENTER);
    gtk_container_set_border_width(GTK_CONTAINER(ventana), 22);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 16);
    gtk_container_add(GTK_CONTAINER(ventana), caja);
    gtk_style_context_add_class(gtk_widget_get_style_context(caja), "pawos-fondo-dinamico");
    gtk_window_maximize(GTK_WINDOW(ventana));
'''

# ---------------------------------------------------------------------------
# Parche 3: registro de clientes -> solo fondo (dialogo de tamano normal)
# ---------------------------------------------------------------------------
ANCLA_REGISTRO = '''static gboolean mostrar_registro_cliente(Cliente *cliente_out) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Crear cuenta de Cliente", NULL, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Crear cuenta", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
'''
NUEVO_REGISTRO = '''static gboolean mostrar_registro_cliente(Cliente *cliente_out) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Crear cuenta de Cliente", NULL, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Crear cuenta", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");
'''

# ---------------------------------------------------------------------------
# Parche 4: login de clientes -> solo fondo (dialogo de tamano normal)
# ---------------------------------------------------------------------------
ANCLA_LOGIN = '''        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,
            "Regresar", GTK_RESPONSE_CANCEL,
            "Registrarme", RESPUESTA_REGISTRARME,
            "Ingresar", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
'''
NUEVO_LOGIN = '''        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Acceso de Clientes", NULL, GTK_DIALOG_MODAL,
            "Regresar", GTK_RESPONSE_CANCEL,
            "Registrarme", RESPUESTA_REGISTRARME,
            "Ingresar", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
        gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");
'''

# ---------------------------------------------------------------------------
# Parche 5: selector inicial -> fondo + pantalla completa (maximizada)
# ---------------------------------------------------------------------------
ANCLA_SELECTOR = '''static TipoEntrada mostrar_selector_entrada(void) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS Refugio", NULL, GTK_DIALOG_MODAL,
        "Salir", GTK_RESPONSE_CANCEL,
        "Soy Colaborador", RESPUESTA_COLABORADOR,
        "Soy Cliente", RESPUESTA_CLIENTE,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
'''
NUEVO_SELECTOR = '''static TipoEntrada mostrar_selector_entrada(void) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS Refugio", NULL, GTK_DIALOG_MODAL,
        "Salir", GTK_RESPONSE_CANCEL,
        "Soy Colaborador", RESPUESTA_COLABORADOR,
        "Soy Cliente", RESPUESTA_CLIENTE,
        NULL);
    gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);
    gtk_style_context_add_class(gtk_widget_get_style_context(dialogo), "pawos-fondo-dinamico");
    gtk_window_maximize(GTK_WINDOW(dialogo));
'''

PARCHES = [
    ("fondo dinamico (CSS)", ANCLA_CSS, NUEVO_CSS),
    ("menu principal (fondo + pantalla completa)", ANCLA_MENU, NUEVO_MENU),
    ("registro de clientes (fondo)", ANCLA_REGISTRO, NUEVO_REGISTRO),
    ("login de clientes (fondo)", ANCLA_LOGIN, NUEVO_LOGIN),
    ("selector inicial (fondo + pantalla completa)", ANCLA_SELECTOR, NUEVO_SELECTOR),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    # Validar los 5 anclajes ANTES de escribir nada.
    for nombre, ancla, _ in PARCHES:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque de '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("No se cambio nada en el archivo.")
            sys.exit(1)

    for _, ancla, nuevo in PARCHES:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak11")
    print(f"Backup creado: {ARCHIVO}.bak11")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK: fondo dinamico agregado en las 4 pantallas.")
    print("")
    print("Compila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
