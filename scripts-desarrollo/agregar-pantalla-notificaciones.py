#!/usr/bin/env python3
"""
agregar-pantalla-notificaciones.py

Agrega la pantalla "Configurar Notificaciones" (solo Administrador) al
dashboard del GUI: un formulario para guardar el correo de Gmail, su
contrasena de aplicacion, y las credenciales de Green API (WhatsApp),
usadas por Agenda de Vacunas para mandar recordatorios de citas.

El formulario NO escribe el archivo de configuracion directo -- llama
(via sudo, con contrasena solo si el usuario no tiene sudo passwordless
para ese comando especifico) al script pawos-configurar-notificaciones,
que es el unico que puede escribir /etc/pawos/notificaciones.conf.

No cambia nada de los modulos existentes -- solo agrega uno nuevo
(indice 10) y lo restringe a Administrador en modulo_permitido(),
igual que "Administrar Colaboradores" (indice 9).

Uso: parado en la raiz del repo:
    python3 agregar-pantalla-notificaciones.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1) modulo_permitido() + nueva funcion on_configurar_notificaciones_clicked()
# ---------------------------------------------------------------
ANCLA_PERMISOS = """static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}

static void construir_ventana_principal(Rol rol, const char *usuario) {"""
NUEVO_PERMISOS = """static gboolean modulo_permitido(Rol rol, int indice) {
    if (rol == ROL_ADMIN) return TRUE;

    switch (rol) {
        case ROL_VETERINARIO:
            return !(indice == 5 || indice == 6 || indice == 9 || indice == 10);
        case ROL_VOLUNTARIO:
            return !(indice == 3 || indice == 4 || indice == 5 || indice == 6 || indice == 9 || indice == 10);
        case ROL_RESCATISTA:
            return (indice == 0 || indice == 8);
        case ROL_RECEPCIONISTA:
            return (indice == 2 || indice == 3);
        default:
            return FALSE;
    }
}

/* Pantalla de Administrador para guardar las credenciales de correo
 * (Gmail) y WhatsApp (Green API) usadas por Agenda de Vacunas para
 * mandar recordatorios de citas. El formulario mismo NO escribe el
 * archivo de configuracion -- solo llama (via sudo) al script
 * pawos-configurar-notificaciones, el unico con permiso de escribir
 * /etc/pawos/notificaciones.conf (protegido, 600, root:root). */
static void on_configurar_notificaciones_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    DatosBotonModulo *d = (DatosBotonModulo *)datos;
    GtkWindow *padre = (d && d->ventana_principal) ? GTK_WINDOW(d->ventana_principal) : NULL;
    if (!d || d->rol != ROL_ADMIN) {
        mostrar_mensaje(padre, "Solo el Administrador puede configurar las notificaciones.", TRUE);
        return;
    }

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Configurar Notificaciones", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL,
        "_Guardar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 420, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_set_border_width(GTK_CONTAINER(grid), 14);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *aviso = gtk_label_new(
        "Credenciales para mandar recordatorios de citas por correo y WhatsApp.\\n"
        "Se guardan protegidas en el sistema (no se muestran de vuelta).");
    gtk_label_set_line_wrap(GTK_LABEL(aviso), TRUE);
    gtk_grid_attach(GTK_GRID(grid), aviso, 0, 0, 2, 1);

    GtkWidget *e_gmail_user = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_user), "correo@gmail.com");
    GtkWidget *e_gmail_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_gmail_pass), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_pass), "Contrasena de aplicacion (16 caracteres)");
    GtkWidget *e_green_url = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_url), "https://XXXX.api.greenapi.com");
    GtkWidget *e_green_id = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_id), "idInstance");
    GtkWidget *e_green_token = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_green_token), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_token), "apiTokenInstance");

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Correo Gmail:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_gmail_user, 1, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Contrasena de app:"), 0, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_gmail_pass, 1, 2, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API URL:"), 0, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_url, 1, 3, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API idInstance:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_id, 1, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Green API apiToken:"), 0, 5, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e_green_token, 1, 5, 1, 1);

    gtk_widget_show_all(dialogo);
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const char *gmail_user = gtk_entry_get_text(GTK_ENTRY(e_gmail_user));
        const char *gmail_pass = gtk_entry_get_text(GTK_ENTRY(e_gmail_pass));
        const char *green_url = gtk_entry_get_text(GTK_ENTRY(e_green_url));
        const char *green_id = gtk_entry_get_text(GTK_ENTRY(e_green_id));
        const char *green_token = gtk_entry_get_text(GTK_ENTRY(e_green_token));

        if (!gmail_user[0] || !gmail_pass[0] || !green_url[0] || !green_id[0] || !green_token[0]) {
            mostrar_mensaje(padre, "Completa todos los campos.", TRUE);
        } else {
            FILE *proceso = popen("sudo /usr/local/bin/pawos-configurar-notificaciones", "w");
            if (!proceso) {
                mostrar_mensaje(padre, "No se pudo iniciar el guardado de la configuracion.", TRUE);
            } else {
                fprintf(proceso, "%s\\n%s\\n%s\\n%s\\n%s\\n", gmail_user, gmail_pass, green_url, green_id, green_token);
                int rc = pclose(proceso);
                if (rc == 0) {
                    mostrar_mensaje(padre, "Configuracion guardada correctamente.", FALSE);
                } else {
                    mostrar_mensaje(padre, "No se pudo guardar la configuracion (revisa permisos de sudo).", TRUE);
                }
            }
        }
    }
    gtk_widget_destroy(dialogo);
}

static void construir_ventana_principal(Rol rol, const char *usuario) {"""

# ---------------------------------------------------------------
# 2) arreglos del dashboard
# ---------------------------------------------------------------
ANCLA_ARREGLOS = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
        "\\xF0\\x9F\\x91\\xA5", /* people */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion",
    };
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
    };
    const int total_modulos = 10;"""
NUEVO_ARREGLOS = """    const char *nombres_modulos[] = {
        "Gestion de Mascotas",
        "Agenda de Vacunas",
        "Control de Adopciones",
        "Base de Donantes",
        "Reportes",
        "Administracion de Procesos",
        "Administracion de Memoria",
        "Respaldo en la Nube",
        "Alertas de Sensores",
        "Administrar Colaboradores",
        "Configurar Notificaciones",
    };
    /* Icono (emoji) por modulo, solo cosmetico -- no afecta la logica. */
    const char *iconos_modulos[] = {
        "\\xF0\\x9F\\x90\\xBE", /* paw */
        "\\xF0\\x9F\\x92\\x89", /* syringe */
        "\\xF0\\x9F\\x8F\\xA0", /* house */
        "\\xF0\\x9F\\x92\\xB0", /* money bag */
        "\\xF0\\x9F\\x93\\x8A", /* bar chart */
        "\\xE2\\x9A\\x99",     /* gear */
        "\\xF0\\x9F\\xA7\\xA0", /* brain */
        "\\xE2\\x98\\x81",     /* cloud */
        "\\xF0\\x9F\\x9A\\xA8", /* siren */
        "\\xF0\\x9F\\x91\\xA5", /* people */
        "\\xF0\\x9F\\x93\\xA7", /* envelope */
    };
    /* Categoria por modulo (solo cosmetica, define el color del boton):
     * refugio = atencion directa al animal, gestion = administrativo,
     * sistema = infraestructura del S.O. */
    const char *categorias_modulos[] = {
        "cat-refugio", "cat-refugio", "cat-refugio", "cat-gestion",
        "cat-gestion", "cat-sistema", "cat-sistema", "cat-gestion", "cat-refugio",
        "cat-gestion", "cat-gestion",
    };
    GCallback manejadores[] = {
        G_CALLBACK(on_mascotas_clicked),
        G_CALLBACK(on_vacunas_clicked),
        G_CALLBACK(on_adopciones_clicked),
        G_CALLBACK(on_donantes_clicked),
        G_CALLBACK(on_reportes_clicked),
        G_CALLBACK(on_procesos_clicked),
        G_CALLBACK(on_memoria_clicked),
        G_CALLBACK(on_respaldo_clicked),
        G_CALLBACK(on_alertas_clicked),
        G_CALLBACK(on_administrar_colaboradores_clicked),
        G_CALLBACK(on_configurar_notificaciones_clicked),
    };
    const int total_modulos = 11;"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    pares = [
        (ANCLA_PERMISOS, NUEVO_PERMISOS, "modulo_permitido + nueva funcion"),
        (ANCLA_ARREGLOS, NUEVO_ARREGLOS, "arreglos del dashboard"),
    ]
    for ancla, _nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak3")
    print(f"Backup creado: {ARCHIVO}.bak3")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")

    print("")
    print("Falta instalar el script pawos-configurar-notificaciones y la")
    print("regla de sudoers antes de compilar y probar (viene en el siguiente paso).")


if __name__ == "__main__":
    main()
