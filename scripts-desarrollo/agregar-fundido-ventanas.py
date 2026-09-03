#!/usr/bin/env python3
"""
agregar-fundido-ventanas.py

Agrega un fundido (fade-in) al abrir cada ventana y dialogo de la app:
en vez de aparecer de golpe, la opacidad sube de 0 a 1 en unos pocos
pasos (~100ms). Usa un temporizador corto de GLib (g_timeout_add) que
se apaga solo al terminar -- no queda nada corriendo de fondo, no
agrega hilos, no deberia ralentizar nada.

No se toca la logica de ningun dialogo: solo se cambia la LLAMADA que
ya existia (gtk_widget_show_all(X)) por una nueva funcion
(mostrar_con_fundido(X)) que hace exactamente lo mismo (gtk_widget_show_all
sigue llamandose adentro) mas la animacion.

Excepcion a proposito: el dialogo "Buscando actualizaciones..." NO se
toca -- ese se muestra a la fuerza con gtk_main_iteration() justo antes
de una operacion bloqueante (git pull), y retrasar su aparicion le
quitaria el proposito (avisar de inmediato que ya empezo a buscar).

Requisito: correr DESPUES de agregar-icono-ver-password.py (usa el
bloque de agregar_boton_ver_password() que ese script dejo como ancla
para saber donde meter las funciones nuevas).

Uso: parado en la raiz del repo:
    python3 agregar-fundido-ventanas.py
"""

import re
import shutil
import sys

ARCHIVO = "src/main_gtk.c"

VARIABLE_EXCLUIDA = "dialogo_buscando"

# ---------------------------------------------------------------
# 1. Funciones nuevas: se insertan justo despues de
#    agregar_boton_ver_password(), antes del comentario del primer
#    modulo (mismo punto donde agregar-icono-ver-password.py dejo sus
#    propias funciones auxiliares).
# ---------------------------------------------------------------
ANCLA_HELPER = """static void agregar_boton_ver_password(GtkWidget *entrada) {
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                       "view-reveal-symbolic");
    gtk_entry_set_icon_tooltip_text(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                     "Mostrar/ocultar contrasena");
    g_signal_connect(entrada, "icon-press", G_CALLBACK(on_click_icono_ver_password), NULL);
}

/* =================================================================
 * Modulo: Gestion de Mascotas
 * ================================================================= */"""
NUEVO_HELPER = """static void agregar_boton_ver_password(GtkWidget *entrada) {
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                       "view-reveal-symbolic");
    gtk_entry_set_icon_tooltip_text(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                     "Mostrar/ocultar contrasena");
    g_signal_connect(entrada, "icon-press", G_CALLBACK(on_click_icono_ver_password), NULL);
}

/* Fundido de entrada (fade-in) para ventanas y dialogos: en vez de
 * aparecer de golpe, la opacidad sube de 0 a 1 en unos pocos pasos
 * (~100ms). El temporizador se apaga solo (G_SOURCE_REMOVE) al llegar
 * a opacidad completa -- no queda nada corriendo de fondo. Se guarda
 * una referencia (g_object_ref) mientras dura la animacion para que no
 * truene si el usuario alcanza a cerrar la ventana antes de que
 * termine. */
static gboolean fundido_tick(gpointer datos) {
    GtkWidget *widget = GTK_WIDGET(datos);
    gdouble opacidad = gtk_widget_get_opacity(widget) + 0.15;
    if (opacidad >= 1.0) {
        gtk_widget_set_opacity(widget, 1.0);
        g_object_unref(widget);
        return G_SOURCE_REMOVE;
    }
    gtk_widget_set_opacity(widget, opacidad);
    return G_SOURCE_CONTINUE;
}

static void mostrar_con_fundido(GtkWidget *ventana) {
    gtk_widget_set_opacity(ventana, 0.0);
    gtk_widget_show_all(ventana);
    g_timeout_add(15, fundido_tick, g_object_ref(ventana));
}

/* =================================================================
 * Modulo: Gestion de Mascotas
 * ================================================================= */"""

# ---------------------------------------------------------------
# 2. Reemplazar gtk_widget_show_all(X) por mostrar_con_fundido(X) en
#    todas las ventanas/dialogos, EXCEPTO dialogo_buscando.
# ---------------------------------------------------------------
PATRON = re.compile(r"gtk_widget_show_all\(([A-Za-z_][A-Za-z0-9_>\-.]*)\);")


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA_HELPER) != 1:
        print("ERROR: no se encontro el bloque de agregar_boton_ver_password().")
        print("       Puede que agregar-icono-ver-password.py no se haya aplicado todavia.")
        print("       No se cambio nada.")
        sys.exit(1)

    coincidencias = PATRON.findall(contenido)
    total = len(coincidencias)
    if total < 30:
        print(f"ERROR: solo se encontraron {total} llamadas a gtk_widget_show_all()," )
        print("       se esperaban varias decenas. No se cambio nada (por seguridad).")
        sys.exit(1)
    if coincidencias.count(VARIABLE_EXCLUIDA) != 1:
        print(f"ERROR: se esperaba exactamente 1 aparicion de '{VARIABLE_EXCLUIDA}',")
        print(f"       se encontraron {coincidencias.count(VARIABLE_EXCLUIDA)}. No se cambio nada.")
        sys.exit(1)

    def reemplazo(m):
        var = m.group(1)
        if var == VARIABLE_EXCLUIDA:
            return m.group(0)
        return f"mostrar_con_fundido({var});"

    # OJO: el reemplazo global se hace ANTES de insertar las funciones
    # nuevas -- mostrar_con_fundido() contiene su propio
    # gtk_widget_show_all(ventana) adentro, y si insertaramos primero
    # el regex se agarraria a si mismo por error.
    contenido_nuevo, n_cambiados = PATRON.subn(reemplazo, contenido)

    esperados = total - 1  # todos menos dialogo_buscando
    if n_cambiados != total:
        print(f"ERROR: se procesaron {n_cambiados} coincidencias, se esperaban {total}.")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido_nuevo = contenido_nuevo.replace(ANCLA_HELPER, NUEVO_HELPER, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak12")
    print(f"Backup creado: {ARCHIVO}.bak12")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido_nuevo)
    print(f"{ARCHIVO} parchado OK: fundido agregado a {esperados} ventanas/dialogos.")
    print(f"(se dejo sin tocar '{VARIABLE_EXCLUIDA}', a proposito.)")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
