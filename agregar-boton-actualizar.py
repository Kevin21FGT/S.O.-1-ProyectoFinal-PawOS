#!/usr/bin/env python3
# agregar-boton-actualizar.py - Inserta el callback y el boton
# "Buscar Actualizaciones" en src/main_gtk.c de forma quirurgica,
# sin tocar nada mas del archivo. Hace un backup antes de escribir.
import sys, re, shutil

RUTA = "src/main_gtk.c"
shutil.copy(RUTA, RUTA + ".bak")

with open(RUTA, "r", encoding="utf-8") as f:
    contenido = f.read()

marcador_func = "static void construir_ventana_principal(Rol rol, const char *usuario) {"
if marcador_func not in contenido:
    print("ERROR: no encontre el marcador de la funcion construir_ventana_principal. No se modifico nada.")
    sys.exit(1)

if "on_actualizar_clicked" in contenido:
    print("El boton de actualizar ya parece estar agregado (se encontro 'on_actualizar_clicked'). No se modifico nada.")
    sys.exit(0)

callback = '''static void on_actualizar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    (void)datos;
    GError *error = NULL;
    gboolean ok = g_spawn_command_line_async(
        "x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error);
    if (!ok) {
        g_warning("No se pudo abrir el actualizador: %s", error ? error->message : "error desconocido");
        if (error) g_error_free(error);
    }
}

'''
contenido = contenido.replace(marcador_func, callback + marcador_func, 1)

marcador_boton = '    GtkWidget *btn_salir = gtk_button_new_with_label("Salir");'
if marcador_boton not in contenido:
    print("ERROR: no encontre el marcador del boton Salir. Restaurando backup.")
    shutil.copy(RUTA + ".bak", RUTA)
    sys.exit(1)

boton = '''    GtkWidget *btn_actualizar = gtk_button_new_with_label("\\xF0\\x9F\\x94\\x84  Buscar Actualizaciones");
    gtk_widget_set_size_request(btn_actualizar, 250, 46);
    gtk_widget_set_halign(btn_actualizar, GTK_ALIGN_CENTER);
    gtk_widget_set_tooltip_text(btn_actualizar, "Busca la ultima version en GitHub y la instala.");
    gtk_box_pack_start(GTK_BOX(caja), btn_actualizar, FALSE, FALSE, 0);
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), NULL);

'''
contenido = contenido.replace(marcador_boton, boton + marcador_boton, 1)

with open(RUTA, "w", encoding="utf-8") as f:
    f.write(contenido)

print("Listo. Backup guardado en " + RUTA + ".bak")
