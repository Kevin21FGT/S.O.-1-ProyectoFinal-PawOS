/* Prueba minima, sin nada de PawOS: una ventana GTK3 con un boton que
 * llama a gtk_window_maximize(). Sirve para aislar si el problema de
 * maximizado es de PawOS o del propio GTK3/gestor de ventanas en esta
 * VM. Compilar con:
 *   gcc $(pkg-config --cflags gtk+-3.0) prueba-maximizar.c -o prueba-maximizar $(pkg-config --libs gtk+-3.0)
 * Ejecutar con:
 *   ./prueba-maximizar
 */
#include <gtk/gtk.h>

static void on_clic(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWindow *ventana = GTK_WINDOW(datos);
    if (gtk_window_is_maximized(ventana)) {
        gtk_window_unmaximize(ventana);
        g_print("Llamando a gtk_window_unmaximize()\n");
    } else {
        gtk_window_maximize(ventana);
        g_print("Llamando a gtk_window_maximize()\n");
    }
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    GtkWidget *ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ventana), "Prueba Maximizar");
    gtk_window_set_default_size(GTK_WINDOW(ventana), 400, 300);
    gtk_window_set_type_hint(GTK_WINDOW(ventana), GDK_WINDOW_TYPE_HINT_NORMAL);
    g_signal_connect(ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *boton = gtk_button_new_with_label("Maximizar / Restaurar");
    g_signal_connect(boton, "clicked", G_CALLBACK(on_clic), ventana);
    gtk_container_add(GTK_CONTAINER(ventana), boton);

    gtk_widget_show_all(ventana);
    gtk_main();
    return 0;
}
