#!/usr/bin/env python3
"""
agregar-acerca-de.py

Agrega un dialogo "Acerca de" (version, descripcion breve, creditos)
accesible desde un boton nuevo en el menu principal, junto a "Buscar
Actualizaciones" y "Salir". No toca la logica de ningun otro boton.

Requisito: correr DESPUES de agregar-fundido-ventanas.py (usa
mostrar_con_fundido() para que el dialogo tambien aparezca con fundido,
igual que el resto de la app).

Uso: parado en la raiz del repo:
    python3 agregar-acerca-de.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. Funcion nueva: se inserta justo despues de on_actualizar_clicked().
# ---------------------------------------------------------------
ANCLA_FUNCION = """    if (respuesta == GTK_RESPONSE_ACCEPT) {
        GError *error_terminal = NULL;
        gboolean ok_terminal = g_spawn_command_line_async(
            "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error_terminal);
        if (!ok_terminal) {
            g_warning("No se pudo abrir el actualizador: %s", error_terminal ? error_terminal->message : "error desconocido");
            if (error_terminal) g_error_free(error_terminal);
        }
    }
}"""
NUEVO_FUNCION = """    if (respuesta == GTK_RESPONSE_ACCEPT) {
        GError *error_terminal = NULL;
        gboolean ok_terminal = g_spawn_command_line_async(
            "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error_terminal);
        if (!ok_terminal) {
            g_warning("No se pudo abrir el actualizador: %s", error_terminal ? error_terminal->message : "error desconocido");
            if (error_terminal) g_error_free(error_terminal);
        }
    }
}

/* Dialogo "Acerca de": version (de include/version.h), descripcion
 * breve y creditos. Solo informativo, no lee ni escribe nada. */
static void on_acerca_de_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Acerca de PawOS Refugio", padre, GTK_DIALOG_MODAL,
        "_Cerrar", GTK_RESPONSE_CLOSE, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 380, -1);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 18);
    gtk_container_add(GTK_CONTAINER(area), caja);

    GtkWidget *titulo = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(titulo),
        "<span size='x-large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
    gtk_widget_set_halign(titulo, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

    gchar *texto_version = g_strdup_printf("Version %s", PAWOS_VERSION);
    GtkWidget *lbl_version = gtk_label_new(texto_version);
    g_free(texto_version);
    gtk_widget_set_halign(lbl_version, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_version, FALSE, FALSE, 0);

    GtkWidget *lbl_desc = gtk_label_new(
        "Sistema de gestion para refugios de animales: mascotas, "
        "vacunas, adopciones, donantes y recordatorios automaticos "
        "de citas por correo y WhatsApp.");
    gtk_label_set_line_wrap(GTK_LABEL(lbl_desc), TRUE);
    gtk_widget_set_halign(lbl_desc, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_desc, FALSE, FALSE, 8);

    GtkWidget *lbl_creditos = gtk_label_new("Proyecto Final de Sistemas Operativos.");
    gtk_widget_set_halign(lbl_creditos, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja), lbl_creditos, FALSE, FALSE, 0);

    mostrar_con_fundido(dialogo);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}"""

# ---------------------------------------------------------------
# 2. Boton nuevo en el menu principal, entre "Buscar Actualizaciones"
#    y "Salir".
# ---------------------------------------------------------------
ANCLA_BOTON = """    GtkWidget *btn_actualizar = gtk_button_new_with_label("\\xF0\\x9F\\x94\\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, 250, 46);
    gtk_widget_set_halign(btn_actualizar, GTK_ALIGN_CENTER);
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(caja), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);

    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");"""
NUEVO_BOTON = """    GtkWidget *btn_actualizar = gtk_button_new_with_label("\\xF0\\x9F\\x94\\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, 250, 46);
    gtk_widget_set_halign(btn_actualizar, GTK_ALIGN_CENTER);
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(caja), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), datos_botones);

    GtkWidget *btn_acerca_de = gtk_button_new_with_label("Acerca de");
    gtk_widget_set_size_request(btn_acerca_de, 250, 46);
    gtk_widget_set_halign(btn_acerca_de, GTK_ALIGN_CENTER);
    gtk_box_pack_start(GTK_BOX(caja), btn_acerca_de, FALSE, FALSE, 0);
    g_signal_connect(btn_acerca_de, "clicked", G_CALLBACK(on_acerca_de_clicked), datos_botones);

    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");"""


def main():
    pares = [
        (ANCLA_FUNCION, NUEVO_FUNCION, "funcion on_acerca_de_clicked()"),
        (ANCLA_BOTON, NUEVO_BOTON, "boton Acerca de en el menu"),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak15")
    print(f"Backup creado: {ARCHIVO}.bak15")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: dialogo 'Acerca de' agregado.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
