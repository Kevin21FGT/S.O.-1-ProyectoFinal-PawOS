#!/usr/bin/env python3
"""
agregar-novedades-dialogo.py

Reemplaza el boton "Buscar Actualizaciones" para que, antes de abrir la
terminal del actualizador, muestre un dialogo nativo de GTK con las
"novedades" de la nueva version (al estilo Google Play / Windows
Update): que hay disponible, un icono por tipo de cambio (novedad,
mejora, correccion), y botones "Actualizar ahora" / "Cancelar".

Si el usuario le da "Actualizar ahora", ahi si se abre la terminal con
pawos-actualizar-gui exactamente igual que antes (ese proceso sigue
necesitando la terminal porque el binario no se puede sobreescribir a
si mismo mientras esta corriendo).

Uso: parado en la raiz del repo (rama-Combinada actualizada):
    python3 agregar-novedades-dialogo.py

Hace backup automatico a src/main_gtk.c.bak antes de tocar nada, y
aborta sin cambiar nada si no encuentra el texto exacto esperado.
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA_FUNCION = '''static void on_actualizar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    (void)datos;
    GError *error = NULL;
    gboolean ok = g_spawn_command_line_async(
        "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error);
    if (!ok) {
        g_warning("No se pudo abrir el actualizador: %s", error ? error->message : "error desconocido");
        if (error) g_error_free(error);
    }
}'''

NUEVA_FUNCION = '''/* Clasifica cada linea del changelog con un icono, al estilo de las
 * notas de version de Google Play / Windows Update (novedad, mejora,
 * correccion de estabilidad). Heuristica simple por palabras clave,
 * solo cosmetica -- no cambia el contenido del mensaje. */
static const char *clasificar_commit_icono(const char *mensaje) {
    gchar *minuscula = g_utf8_strdown(mensaje, -1);
    const char *icono;
    if (strstr(minuscula, "arregla") || strstr(minuscula, "corrige") ||
        strstr(minuscula, "arreglo") || strstr(minuscula, "error") ||
        strstr(minuscula, "bug") || strstr(minuscula, "fix")) {
        icono = "\\xF0\\x9F\\x94\\xA7"; /* llave inglesa = estabilidad */
    } else if (strstr(minuscula, "mejora") || strstr(minuscula, "optimiza") ||
               strstr(minuscula, "profesional") || strstr(minuscula, "diseno") ||
               strstr(minuscula, "dise\\xC3\\xB1o")) {
        icono = "\\xE2\\xAD\\x90"; /* estrella = mejora */
    } else {
        icono = "\\xE2\\x9C\\xA8"; /* destellos = novedad */
    }
    g_free(minuscula);
    return icono;
}

static void on_actualizar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;

    GtkWidget *dialogo_buscando = gtk_message_dialog_new(
        padre, GTK_DIALOG_MODAL, GTK_MESSAGE_INFO, GTK_BUTTONS_NONE,
        "Buscando actualizaciones...");
    gtk_widget_show_all(dialogo_buscando);
    while (gtk_events_pending()) gtk_main_iteration();

    gchar *salida = NULL;
    gchar *error_salida = NULL;
    gint estado_salida = 0;
    GError *error = NULL;
    const gchar *comando =
        "bash -c '"
        "REPO_DIR=/opt/pawos-src; RAMA=rama-Kevin; "
        "if [ -d \\"$REPO_DIR/.git\\" ]; then "
        "  cd \\"$REPO_DIR\\" || { echo SIN_CONEXION; exit 0; }; "
        "  git fetch origin \\"$RAMA\\" >/dev/null 2>&1 || { echo SIN_CONEXION; exit 0; }; "
        "  LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse origin/$RAMA); "
        "  if [ \\"$LOCAL\\" = \\"$REMOTE\\" ]; then echo AL_DIA; "
        "  else echo HAY_CAMBIOS; git log \\"$LOCAL..$REMOTE\\" --pretty=format:%s; fi; "
        "else echo PRIMERA_VEZ; fi'";

    gboolean ok = g_spawn_command_line_sync(comando, &salida, &error_salida, &estado_salida, &error);
    gtk_widget_destroy(dialogo_buscando);
    g_free(error_salida);

    if (!ok) {
        mostrar_mensaje(padre, "No se pudo buscar actualizaciones. Revisa tu conexion a internet.", TRUE);
        if (error) g_error_free(error);
        g_free(salida);
        return;
    }

    gchar **lineas = g_strsplit(salida ? salida : "", "\\n", -1);
    g_free(salida);
    const char *estado = lineas[0] ? lineas[0] : "";

    if (g_strcmp0(estado, "SIN_CONEXION") == 0) {
        mostrar_mensaje(padre, "No se pudo conectar para buscar actualizaciones.\\nRevisa tu conexion a internet.", TRUE);
        g_strfreev(lineas);
        return;
    }
    if (g_strcmp0(estado, "AL_DIA") == 0) {
        mostrar_mensaje(padre, "Ya tienes la ultima version instalada.", FALSE);
        g_strfreev(lineas);
        return;
    }

    /* HAY_CAMBIOS o PRIMERA_VEZ: mostramos el dialogo de novedades,
     * al estilo de una tienda de aplicaciones. */
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "PawOS - Actualizaciones", padre, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
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

    gtk_widget_show_all(dialogo);
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
}'''

ANCLA_CONNECT = 'g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), NULL);'
NUEVA_CONNECT = 'g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA_FUNCION) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el texto exacto de")
        print("       on_actualizar_clicked que este script espera. Puede que el archivo")
        print("       ya haya sido modificado. No se cambio nada.")
        sys.exit(1)

    if contenido.count(ANCLA_CONNECT) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) la linea de")
        print("       g_signal_connect esperada. No se cambio nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak")
    print(f"Backup creado: {ARCHIVO}.bak")

    contenido = contenido.replace(ANCLA_FUNCION, NUEVA_FUNCION, 1)
    contenido = contenido.replace(ANCLA_CONNECT, NUEVA_CONNECT, 1)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")


if __name__ == "__main__":
    main()
