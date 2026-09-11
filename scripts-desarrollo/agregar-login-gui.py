#!/usr/bin/env python3
"""
agregar-login-gui.py

Quita el login basado en grupos de Linux (auth_usuario_actual /
auth_rol_actual) del arranque de PawOS Refugio GUI, y lo reemplaza por
una pantalla de inicio de sesion DENTRO del propio programa: usuario y
contrasena, validados contra la tabla "usuarios" de la base de datos
(la misma tabla y la misma funcion usuario_autenticar() que ya usa la
version de texto en pantalla_login.c -- no se inventa nada nuevo del
lado de la base de datos, solo se le hace un dialogo grafico).

Hasta 3 intentos, igual que la version de texto. Si se agotan los
intentos o el usuario le da "Salir", el programa se cierra sin abrir
la ventana principal.

Uso: parado en la raiz del repo:
    python3 agregar-login-gui.py

Hace backup automatico a src/main_gtk.c.bak3 antes de tocar nada, y
aborta sin cambiar nada si no encuentra el texto exacto esperado.
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA_FUNCION = '''/* ---------------------------------------------------------------
 * main
 * --------------------------------------------------------------- */

int main(int argc, char **argv) {'''

NUEVA_FUNCION = '''/* ---------------------------------------------------------------
 * main
 * --------------------------------------------------------------- */

/* Muestra el dialogo de inicio de sesion de PawOS (usuario/contrasena),
 * usando la misma tabla "usuarios" y la misma funcion de autenticacion
 * (usuario_autenticar() en db.c, contrasenas guardadas como hash) que ya
 * usa la version de texto (pantalla_login.c) -- ya NO se usa el usuario
 * de Linux ni sus grupos para decidir el rol. Hasta 3 intentos, igual
 * que la version de texto. Devuelve TRUE y llena usuario_out/rol_out si
 * el login fue correcto, o FALSE si cancelo o agoto los intentos (en
 * ambos casos el programa debe cerrarse sin abrir la ventana principal). */
static gboolean mostrar_login_gtk(char *usuario_out, size_t usuario_len, Rol *rol_out) {
    int intentos = 0;
    const int max_intentos = 3;

    while (intentos < max_intentos) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Inicio de sesion", NULL, GTK_DIALOG_MODAL,
            "Salir", GTK_RESPONSE_CANCEL,
            "Ingresar", GTK_RESPONSE_ACCEPT,
            NULL);
        gtk_window_set_position(GTK_WINDOW(dialogo), GTK_WIN_POS_CENTER);

        GtkWidget *area_contenido = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        gtk_container_set_border_width(GTK_CONTAINER(caja), 14);
        gtk_container_add(GTK_CONTAINER(area_contenido), caja);

        GtkWidget *titulo = gtk_label_new(NULL);
        gtk_label_set_markup(GTK_LABEL(titulo),
            "<span size='large' weight='bold'>\\xF0\\x9F\\x90\\xBE PawOS Refugio</span>");
        gtk_box_pack_start(GTK_BOX(caja), titulo, FALSE, FALSE, 0);

        GtkWidget *grid = gtk_grid_new();
        gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
        gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
        gtk_box_pack_start(GTK_BOX(caja), grid, FALSE, FALSE, 0);

        GtkWidget *lbl_usuario = gtk_label_new("Usuario:");
        gtk_widget_set_halign(lbl_usuario, GTK_ALIGN_END);
        GtkWidget *entrada_usuario = gtk_entry_new();
        gtk_grid_attach(GTK_GRID(grid), lbl_usuario, 0, 0, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_usuario, 1, 0, 1, 1);

        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_usuario), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);
        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_ACCEPT);

        if (intentos > 0) {
            GtkWidget *lbl_error = gtk_label_new(NULL);
            gtk_widget_set_halign(lbl_error, GTK_ALIGN_START);
            gchar *texto_error = g_strdup_printf(
                "<span foreground='red'>Usuario o contrasena incorrectos. Intento %d de %d.</span>",
                intentos, max_intentos);
            gtk_label_set_markup(GTK_LABEL(lbl_error), texto_error);
            g_free(texto_error);
            gtk_box_pack_start(GTK_BOX(caja), lbl_error, FALSE, FALSE, 0);
        }

        gtk_widget_show_all(dialogo);
        gint respuesta = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (respuesta != GTK_RESPONSE_ACCEPT) {
            gtk_widget_destroy(dialogo);
            return FALSE;
        }

        const char *usuario_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_usuario));
        const char *password_ingresado = gtk_entry_get_text(GTK_ENTRY(entrada_password));

        int rol_db = -1;
        gboolean ok = (usuario_autenticar(usuario_ingresado, password_ingresado, &rol_db) == 0);

        if (ok) {
            snprintf(usuario_out, usuario_len, "%s", usuario_ingresado);
            *rol_out = (Rol)rol_db;
            gtk_widget_destroy(dialogo);
            return TRUE;
        }

        gtk_widget_destroy(dialogo);
        intentos++;
    }

    GtkWidget *aviso = gtk_message_dialog_new(
        NULL, GTK_DIALOG_MODAL, GTK_MESSAGE_ERROR, GTK_BUTTONS_OK,
        "Demasiados intentos fallidos. Cerrando PawOS.");
    gtk_dialog_run(GTK_DIALOG(aviso));
    gtk_widget_destroy(aviso);
    return FALSE;
}

int main(int argc, char **argv) {'''

ANCLA_LOGICA = '''    const char *usuario = auth_usuario_actual();
    Rol rol = auth_rol_actual();

    construir_ventana_principal(rol, usuario);
    gtk_main();

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto, %s.\\n", usuario);
    return 0;
}'''

NUEVA_LOGICA = '''    char usuario[32] = "";
    Rol rol;
    if (!mostrar_login_gtk(usuario, sizeof(usuario), &rol)) {
        db_close();
        return 0;
    }

    construir_ventana_principal(rol, usuario);
    gtk_main();

    db_close();
    printf("Sesion grafica de PawOS finalizada. Hasta pronto, %s.\\n", usuario);
    return 0;
}'''


def aplicar(contenido, ancla, nuevo, nombre):
    if contenido.count(ancla) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
        print("       Puede que el archivo ya haya sido modificado. No se cambio nada.")
        sys.exit(1)
    return contenido.replace(ancla, nuevo, 1)


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    original = contenido
    contenido = aplicar(contenido, ANCLA_FUNCION, NUEVA_FUNCION, "funcion main / login")
    contenido = aplicar(contenido, ANCLA_LOGICA, NUEVA_LOGICA, "cuerpo de main")

    shutil.copy(ARCHIVO, ARCHIVO + ".bak3")
    print(f"Backup creado: {ARCHIVO}.bak3")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} parchado OK.")
    print("")
    print("Ahora corre:  make clean-gui && make gui")
    print("")
    print("Usuarios de prueba (ya sembrados en la base de datos):")
    print("  admin_refugio / admin123   (Administrador)")
    print("  veterinario1  / vet123     (Veterinario)")
    print("  voluntario1   / vol123     (Voluntario)")


if __name__ == "__main__":
    main()
