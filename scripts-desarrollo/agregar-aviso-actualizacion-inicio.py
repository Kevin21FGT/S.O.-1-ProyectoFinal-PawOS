#!/usr/bin/env python3
"""
agregar-aviso-actualizacion-inicio.py

Al abrir PawOS (antes del login), revisa en silencio si hay una
version nueva en GitHub -- sin mostrar el dialogo de "Buscando...",
para no interrumpir el arranque si no hay nada nuevo. Si SI hay una
version nueva (o es la primera instalacion), muestra un aviso con
"Mas tarde" / "Actualizar ahora", igual de estilo que el que ya existe
en el boton "Buscar Actualizaciones".

No modifica on_actualizar_clicked() ni el boton existente -- es una
funcion nueva y separada, para no arriesgar nada de lo que ya esta
funcionando y probado.

Uso: parado en la raiz del repo:
    python3 agregar-aviso-actualizacion-inicio.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. Funcion nueva: se inserta justo despues de on_acerca_de_clicked().
# ---------------------------------------------------------------
ANCLA_FUNCION = """    GtkWidget *lbl_creditos = gtk_label_new("Proyecto Final de Sistemas Operativos.");
    gtk_widget_set_halign(lbl_creditos, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_creditos, FALSE, FALSE, 0);

    mostrar_con_fundido(dialogo);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}"""
NUEVO_FUNCION = """    GtkWidget *lbl_creditos = gtk_label_new("Proyecto Final de Sistemas Operativos.");
    gtk_widget_set_halign(lbl_creditos, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_creditos, FALSE, FALSE, 0);

    mostrar_con_fundido(dialogo);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

/* Revisa en silencio (sin dialogo de "Buscando...") si hay una
 * version nueva en GitHub, para el aviso automatico al arrancar el
 * programa. Si no hay nada que avisar (ya esta al dia, sin conexion,
 * o fallo el chequeo) no hace nada -- el arranque sigue normal, sin
 * interrumpir al usuario con un mensaje que no aporta nada. */
static void revisar_actualizaciones_al_iniciar(void) {
    gchar *salida = NULL;
    gchar *error_salida = NULL;
    gint estado_salida = 0;
    GError *error = NULL;
    const gchar *comando =
        "bash -c '"
        "REPO_DIR=/opt/pawos-src; RAMA=rama-Kevin; "
        "git config --global --add safe.directory \\"$REPO_DIR\\" 2>/dev/null; "
        "if [ -d \\"$REPO_DIR/.git\\" ]; then "
        "  cd \\"$REPO_DIR\\" || { echo SIN_CONEXION; exit 0; }; "
        "  git fetch origin \\"$RAMA\\" >/dev/null 2>&1 || { echo SIN_CONEXION; exit 0; }; "
        "  LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse origin/$RAMA); "
        "  if [ \\"$LOCAL\\" = \\"$REMOTE\\" ]; then echo AL_DIA; "
        "  else echo HAY_CAMBIOS; git log \\"$LOCAL..$REMOTE\\" --no-merges --pretty=format:%s; fi; "
        "else echo PRIMERA_VEZ; fi'";

    gboolean ok = g_spawn_command_line_sync(comando, &salida, &error_salida, &estado_salida, &error);
    g_free(error_salida);
    if (error) g_error_free(error);
    if (!ok) {
        g_free(salida);
        return;
    }

    gchar **lineas = g_strsplit(salida ? salida : "", "\\n", -1);
    g_free(salida);
    const char *estado = lineas[0] ? lineas[0] : "";

    if (g_strcmp0(estado, "HAY_CAMBIOS") != 0 && g_strcmp0(estado, "PRIMERA_VEZ") != 0) {
        /* Al dia, sin conexion, o algo fallo: no interrumpe el
         * arranque con ningun aviso. */
        g_strfreev(lineas);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS - Actualizacion disponible", NULL, GTK_DIALOG_MODAL,
        "Mas tarde", GTK_RESPONSE_CANCEL,
        "Actualizar ahora", GTK_RESPONSE_ACCEPT,
        NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 460, 420);

    GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area_contenido), 16);

    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_container_add(GTK_CONTAINER(area_contenido), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    if (g_strcmp0(estado, "PRIMERA_VEZ") == 0) {
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\\xF0\\x9F\\x93\\xA5 Version disponible para instalar</span>");
    } else {
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\\xF0\\x9F\\x94\\x84 Nueva version disponible</span>");
    }
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    GtkWidget *subtitulo = gtk_label_new(
        g_strcmp0(estado, "PRIMERA_VEZ") == 0
            ? "Se instalara PawOS Refugio por primera vez en este equipo."
            : "Novedades, mejoras y correcciones de esta actualizacion:");
    gtk_widget_set_halign(subtitulo, GTK_ALIGN_START);
    gtk_label_set_line_wrap(GTK_LABEL(subtitulo), TRUE);
    gtk_box_pack_start(GTK_BOX(caja), subtitulo, FALSE, FALSE, 0);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);
    gtk_box_pack_start(GTK_BOX(caja), scroll, TRUE, TRUE, 0);

    GtkWidget *lista_novedades = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_container_add(GTK_CONTAINER(scroll), lista_novedades);

    int total_items = 0;
    for (int i = 1; lineas[i] != NULL && total_items < 40; i++) {
        if (lineas[i][0] == '\\0') continue;
        const char *icono = clasificar_commit_icono(lineas[i]);
        gchar *texto_item = g_strdup_printf("%s  %s", icono, lineas[i]);
        GtkWidget *lbl_item = gtk_label_new(texto_item);
        g_free(texto_item);
        gtk_label_set_line_wrap(GTK_LABEL(lbl_item), TRUE);
        gtk_widget_set_halign(lbl_item, GTK_ALIGN_START);
        gtk_box_pack_start(GTK_BOX(lista_novedades), lbl_item, FALSE, FALSE, 0);
        total_items++;
    }
    if (total_items == 0) {
        GtkWidget *lbl_vacio = gtk_label_new("(Sin detalle de cambios disponible)");
        gtk_box_pack_start(GTK_BOX(lista_novedades), lbl_vacio, FALSE, FALSE, 0);
    }
    g_strfreev(lineas);

    mostrar_con_fundido(dialogo);
    gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);

    if (respuesta == GTK_RESPONSE_ACCEPT) {
        GError *error_terminal = NULL;
        gboolean ok_terminal = g_spawn_command_line_async(
            "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error_terminal);
        if (!ok_terminal) {
            g_warning("No se pudo abrir el actualizador: %s", error_terminal ? error_terminal->message : "error desconocido");
            if (error_terminal) g_error_free(error_terminal);
        }
    }
}"""

# ---------------------------------------------------------------
# 2. main(): llamarla justo antes del login (despues del asistente de
#    bienvenida de Administrador, antes del bucle de seleccion).
# ---------------------------------------------------------------
ANCLA_MAIN = """    if (!existe_admin()) {
        mostrar_asistente_bienvenida();
    }

    for (;;) {
        TipoEntrada entrada = mostrar_selector_entrada();"""
NUEVO_MAIN = """    if (!existe_admin()) {
        mostrar_asistente_bienvenida();
    }

    revisar_actualizaciones_al_iniciar();

    for (;;) {
        TipoEntrada entrada = mostrar_selector_entrada();"""


def main():
    pares = [
        (ANCLA_FUNCION, NUEVO_FUNCION, "funcion revisar_actualizaciones_al_iniciar()"),
        (ANCLA_MAIN, NUEVO_MAIN, "llamada en main()"),
    ]
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak23")
    print(f"Backup creado: {ARCHIVO}.bak23")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: aviso automatico de actualizacion al iniciar.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
