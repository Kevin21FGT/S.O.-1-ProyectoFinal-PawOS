#!/usr/bin/env python3
"""
arreglar-modo-oscuro-automatico.py

El modo claro/oscuro automatico de PawOS ya existia (aplicar_estilos(),
modo_oscuro_activo(), y una suscripcion para reaplicar estilos si
cambia el tema), pero revisaba las senales VIEJAS de GTK
(gtk-application-prefer-dark-theme / gtk-theme-name), que en GNOME
moderno (Debian 13) ya no se usan para el interruptor de "Oscuro" de
Configuracion del Sistema -- por eso nunca se detectaba el cambio, ni
siquiera reabriendo la app.

Este parche:
  1. Hace que modo_oscuro_activo() revise primero la llave real que usa
     GNOME (org.gnome.desktop.interface / color-scheme), con la logica
     vieja como respaldo para otros escritorios (XFCE, etc.).
  2. En main(), agrega una suscripcion a esa misma llave para que, si
     cambias el tema en Configuracion del Sistema MIENTRAS PawOS esta
     abierto, se actualice solo, sin cerrar y volver a abrir.
  3. Cambia el fondo claro de un blanco-verdoso palido (#EDF2EA) a un
     gris neutro (#F2F3F5), y el fondo de los dialogos a blanco puro
     (#FFFFFF) -- para que ya no se sienta "blanco plano" y se vea mas
     como tarjetas modernas sobre un fondo gris. El modo oscuro y los
     colores de marca (verde) no cambian.

No agrega ningun interruptor propio dentro de la app -- sigue siendo
100% automatico, tal como ya estaba pensado.

Uso: parado en la raiz del repo:
    python3 arreglar-modo-oscuro-automatico.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. modo_oscuro_activo(): revisar primero la llave real de GNOME
# ---------------------------------------------------------------
ANCLA_DETECCION = """static gboolean modo_oscuro_activo(void) {
    GtkSettings *settings = gtk_settings_get_default();
    if (!settings) return FALSE;

    gboolean prefiere_oscuro = FALSE;
    g_object_get(settings, "gtk-application-prefer-dark-theme", &prefiere_oscuro, NULL);
    if (prefiere_oscuro) return TRUE;

    gchar *nombre_tema = NULL;
    g_object_get(settings, "gtk-theme-name", &nombre_tema, NULL);
    gboolean tema_oscuro = (nombre_tema != NULL && strstr(nombre_tema, "dark") != NULL);
    g_free(nombre_tema);
    return tema_oscuro;
}"""
NUEVO_DETECCION = """static gboolean modo_oscuro_activo(void) {
    /* Fuente principal: la preferencia real de GNOME moderno
     * (Configuracion > Apariencia > Oscuro). Se guarda en
     * org.gnome.desktop.interface/color-scheme -- NO en
     * gtk-application-prefer-dark-theme ni en gtk-theme-name (las que
     * se revisaban antes; por eso nunca se detectaba el cambio, ni
     * siquiera reabriendo la app). */
    GSettingsSchemaSource *fuente = g_settings_schema_source_get_default();
    if (fuente) {
        GSettingsSchema *esquema = g_settings_schema_source_lookup(
            fuente, "org.gnome.desktop.interface", TRUE);
        if (esquema) {
            g_settings_schema_unref(esquema);
            GSettings *ajustes = g_settings_new("org.gnome.desktop.interface");
            gchar *esquema_color = g_settings_get_string(ajustes, "color-scheme");
            gboolean prefiere_oscuro_gnome =
                (esquema_color != NULL && strcmp(esquema_color, "prefer-dark") == 0);
            g_free(esquema_color);
            g_object_unref(ajustes);
            if (prefiere_oscuro_gnome) return TRUE;
        }
    }

    /* Respaldo para escritorios sin ese ajuste de GNOME (XFCE, etc.):
     * la preferencia clasica de GTK. */
    GtkSettings *settings = gtk_settings_get_default();
    if (!settings) return FALSE;

    gboolean prefiere_oscuro = FALSE;
    g_object_get(settings, "gtk-application-prefer-dark-theme", &prefiere_oscuro, NULL);
    if (prefiere_oscuro) return TRUE;

    gchar *nombre_tema = NULL;
    g_object_get(settings, "gtk-theme-name", &nombre_tema, NULL);
    gboolean tema_oscuro = (nombre_tema != NULL && strstr(nombre_tema, "dark") != NULL);
    g_free(nombre_tema);
    return tema_oscuro;
}"""

# ---------------------------------------------------------------
# 2. Colores del modo claro: gris neutro en vez de blanco-verdoso
# ---------------------------------------------------------------
ANCLA_COLORES = """    const char *fondo_ventana    = oscuro ? "#1B211C" : "#EDF2EA";
    const char *color_texto      = oscuro ? "#E7ECE4" : "#1C2620";
    const char *fondo_dialogo    = oscuro ? "#232B24" : "#F7FAF6";"""
NUEVO_COLORES = """    const char *fondo_ventana    = oscuro ? "#1B211C" : "#F2F3F5";
    const char *color_texto      = oscuro ? "#E7ECE4" : "#1C2620";
    const char *fondo_dialogo    = oscuro ? "#232B24" : "#FFFFFF";"""

# ---------------------------------------------------------------
# 3. main(): suscribirse tambien a la llave real de GNOME
# ---------------------------------------------------------------
ANCLA_MAIN = """    aplicar_estilos();
    GtkSettings *settings_sistema = gtk_settings_get_default();
    if (settings_sistema) {
        g_signal_connect(settings_sistema, "notify::gtk-application-prefer-dark-theme",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
        g_signal_connect(settings_sistema, "notify::gtk-theme-name",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
    }"""
NUEVO_MAIN = """    aplicar_estilos();
    GtkSettings *settings_sistema = gtk_settings_get_default();
    if (settings_sistema) {
        g_signal_connect(settings_sistema, "notify::gtk-application-prefer-dark-theme",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
        g_signal_connect(settings_sistema, "notify::gtk-theme-name",
                          G_CALLBACK(on_cambio_tema_sistema), NULL);
    }
    /* Escucha en caliente el ajuste real de GNOME (ver comentario en
     * modo_oscuro_activo): si el usuario cambia claro/oscuro en
     * Configuracion del Sistema mientras PawOS esta abierto, esto
     * reaplica los estilos al instante, sin cerrar y volver a abrir.
     * Se deja vivo el resto de la ejecucion a proposito, para seguir
     * escuchando. */
    GSettingsSchemaSource *fuente_ajustes = g_settings_schema_source_get_default();
    if (fuente_ajustes) {
        GSettingsSchema *esquema_interfaz = g_settings_schema_source_lookup(
            fuente_ajustes, "org.gnome.desktop.interface", TRUE);
        if (esquema_interfaz) {
            g_settings_schema_unref(esquema_interfaz);
            GSettings *ajustes_interfaz = g_settings_new("org.gnome.desktop.interface");
            g_signal_connect(ajustes_interfaz, "changed::color-scheme",
                              G_CALLBACK(on_cambio_tema_sistema), NULL);
        }
    }"""


def main():
    pares = [
        (ANCLA_DETECCION, NUEVO_DETECCION, "modo_oscuro_activo()"),
        (ANCLA_COLORES, NUEVO_COLORES, "colores de fondo del modo claro"),
        (ANCLA_MAIN, NUEVO_MAIN, "suscripcion en main()"),
    ]

    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak6")
    print(f"Backup creado: {ARCHIVO}.bak6")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("")
    print("Prueba: abre PawOS, y CON LA APP ABIERTA cambia el tema en")
    print("Configuracion del Sistema > Apariencia (Claro/Oscuro/Auto) --")
    print("deberia cambiar solo, sin cerrar la app.")


if __name__ == "__main__":
    main()
