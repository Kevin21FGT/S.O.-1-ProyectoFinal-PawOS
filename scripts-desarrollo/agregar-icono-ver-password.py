#!/usr/bin/env python3
"""
agregar-icono-ver-password.py

Agrega un icono de "ojo" (mostrar/ocultar) dentro de los 9 campos de
contrasena de la app (login de Colaborador, login de Cliente, registro
de Cliente, editar cuenta de Cliente, registrar Colaborador, crear
Administrador, configurar notificaciones -- Gmail y Green API token).

Usa una sola funcion reutilizable (agregar_boton_ver_password), en vez
de repetir el codigo 9 veces: gtk_entry_set_icon_from_icon_name() con
GTK_ENTRY_ICON_SECONDARY, alternando gtk_entry_set_visibility() al
hacer clic en el icono (senal "icon-press").

Uso: parado en la raiz del repo:
    python3 agregar-icono-ver-password.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 0. Funciones auxiliares nuevas: se insertan justo despues de
#    on_cambio_tema_sistema(), antes del comentario del primer modulo.
# ---------------------------------------------------------------
ANCLA_HELPER = """static void on_cambio_tema_sistema(GObject *obj, GParamSpec *pspec, gpointer datos) {
    (void)obj;
    (void)pspec;
    (void)datos;
    aplicar_estilos();
}

/* =================================================================
 * Modulo: Gestion de Mascotas
 * ================================================================= */"""
NUEVO_HELPER = """static void on_cambio_tema_sistema(GObject *obj, GParamSpec *pspec, gpointer datos) {
    (void)obj;
    (void)pspec;
    (void)datos;
    aplicar_estilos();
}

/* Icono de "ojo" para mostrar/ocultar el texto de un campo de
 * contrasena, reutilizable en todos los formularios de la app (login,
 * registro, configuracion de notificaciones, etc.). Al hacer clic en
 * el icono alterna gtk_entry_set_visibility() y cambia el icono para
 * reflejar el estado actual. */
static void on_click_icono_ver_password(GtkEntry *entrada, GtkEntryIconPosition posicion,
                                          GdkEvent *evento, gpointer datos) {
    (void)evento;
    (void)datos;
    if (posicion != GTK_ENTRY_ICON_SECONDARY) return;
    gboolean visible = gtk_entry_get_visibility(entrada);
    gtk_entry_set_visibility(entrada, !visible);
    gtk_entry_set_icon_from_icon_name(entrada, GTK_ENTRY_ICON_SECONDARY,
        !visible ? "view-conceal-symbolic" : "view-reveal-symbolic");
}

static void agregar_boton_ver_password(GtkWidget *entrada) {
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                       "view-reveal-symbolic");
    gtk_entry_set_icon_tooltip_text(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                     "Mostrar/ocultar contrasena");
    g_signal_connect(entrada, "icon-press", G_CALLBACK(on_click_icono_ver_password), NULL);
}

/* =================================================================
 * Modulo: Gestion de Mascotas
 * ================================================================= */"""

# ---------------------------------------------------------------
# 1. entrada_pass -- dialogo "Registrar Colaborador" (con rol y foto)
# ---------------------------------------------------------------
ANCLA_1 = """    GtkWidget *lbl_pass = gtk_label_new("Contrasena:");
    gtk_widget_set_halign(lbl_pass, GTK_ALIGN_END);
    GtkWidget *entrada_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entrada_pass), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass), GTK_INPUT_PURPOSE_PASSWORD);
    gtk_grid_attach(GTK_GRID(grid), lbl_pass, 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entrada_pass, 1, 1, 1, 1);"""
NUEVO_1 = """    GtkWidget *lbl_pass = gtk_label_new("Contrasena:");
    gtk_widget_set_halign(lbl_pass, GTK_ALIGN_END);
    GtkWidget *entrada_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entrada_pass), FALSE);
    agregar_boton_ver_password(entrada_pass);
    gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass), GTK_INPUT_PURPOSE_PASSWORD);
    gtk_grid_attach(GTK_GRID(grid), lbl_pass, 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entrada_pass, 1, 1, 1, 1);"""

# ---------------------------------------------------------------
# 2. e_gmail_pass -- Configurar Notificaciones (contrasena de app Gmail)
# ---------------------------------------------------------------
ANCLA_2 = """    GtkWidget *e_gmail_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_gmail_pass), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_pass), "Contrasena de aplicacion (16 caracteres)");"""
NUEVO_2 = """    GtkWidget *e_gmail_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_gmail_pass), FALSE);
    agregar_boton_ver_password(e_gmail_pass);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_gmail_pass), "Contrasena de aplicacion (16 caracteres)");"""

# ---------------------------------------------------------------
# 3. e_green_token -- Configurar Notificaciones (Green API apiToken)
# ---------------------------------------------------------------
ANCLA_3 = """    GtkWidget *e_green_token = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_green_token), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_token), "apiTokenInstance");"""
NUEVO_3 = """    GtkWidget *e_green_token = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_green_token), FALSE);
    agregar_boton_ver_password(e_green_token);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_green_token), "apiTokenInstance");"""

# ---------------------------------------------------------------
# 4. e_password -- Cliente: "Editar mi cuenta"
# ---------------------------------------------------------------
ANCLA_4 = """    GtkWidget *e_nombre = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(e_nombre), ctx->nombre_cliente);
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_password), "(dejar en blanco para no cambiarla)");"""
NUEVO_4 = """    GtkWidget *e_nombre = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(e_nombre), ctx->nombre_cliente);
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    agregar_boton_ver_password(e_password);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);
    gtk_entry_set_placeholder_text(GTK_ENTRY(e_password), "(dejar en blanco para no cambiarla)");"""

# ---------------------------------------------------------------
# 5. e_password -- Cliente: "Crear cuenta de Cliente" (registro)
# ---------------------------------------------------------------
ANCLA_5 = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_correo = gtk_entry_new();
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);"""
NUEVO_5 = """    GtkWidget *e_nombre = gtk_entry_new();
    GtkWidget *e_correo = gtk_entry_new();
    GtkWidget *e_password = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(e_password), FALSE);
    agregar_boton_ver_password(e_password);
    gtk_entry_set_input_purpose(GTK_ENTRY(e_password), GTK_INPUT_PURPOSE_PASSWORD);"""

# ---------------------------------------------------------------
# 6. entrada_password -- Login de Clientes (mostrar_login_cliente)
# ---------------------------------------------------------------
ANCLA_6 = """        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_correo), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);"""
NUEVO_6 = """        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        agregar_boton_ver_password(entrada_password);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_correo), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);"""

# ---------------------------------------------------------------
# 7. entrada_password -- Login de Colaborador (mostrar_login_gtk)
# ---------------------------------------------------------------
ANCLA_7 = """        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_usuario), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);"""
NUEVO_7 = """        GtkWidget *lbl_password = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_password, GTK_ALIGN_END);
        GtkWidget *entrada_password = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_password), FALSE);
        agregar_boton_ver_password(entrada_password);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_password), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_password, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_password, 1, 1, 1, 1);

        gtk_entry_set_activates_default(GTK_ENTRY(entrada_usuario), TRUE);
        gtk_entry_set_activates_default(GTK_ENTRY(entrada_password), TRUE);"""

# ---------------------------------------------------------------
# 8. entrada_pass -- "Crear Administrador" (primer arranque)
# ---------------------------------------------------------------
ANCLA_8 = """        GtkWidget *lbl_pass = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_pass, GTK_ALIGN_END);
        GtkWidget *entrada_pass = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass, 1, 1, 1, 1);"""
NUEVO_8 = """        GtkWidget *lbl_pass = gtk_label_new("Contrasena:");
        gtk_widget_set_halign(lbl_pass, GTK_ALIGN_END);
        GtkWidget *entrada_pass = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass), FALSE);
        agregar_boton_ver_password(entrada_pass);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass, 0, 1, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass, 1, 1, 1, 1);"""

# ---------------------------------------------------------------
# 9. entrada_pass2 -- "Crear Administrador", confirmar contrasena
# ---------------------------------------------------------------
ANCLA_9 = """        GtkWidget *lbl_pass2 = gtk_label_new("Confirmar:");
        gtk_widget_set_halign(lbl_pass2, GTK_ALIGN_END);
        GtkWidget *entrada_pass2 = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass2), FALSE);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass2), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass2, 0, 2, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass2, 1, 2, 1, 1);"""
NUEVO_9 = """        GtkWidget *lbl_pass2 = gtk_label_new("Confirmar:");
        gtk_widget_set_halign(lbl_pass2, GTK_ALIGN_END);
        GtkWidget *entrada_pass2 = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entrada_pass2), FALSE);
        agregar_boton_ver_password(entrada_pass2);
        gtk_entry_set_input_purpose(GTK_ENTRY(entrada_pass2), GTK_INPUT_PURPOSE_PASSWORD);
        gtk_grid_attach(GTK_GRID(grid), lbl_pass2, 0, 2, 1, 1);
        gtk_grid_attach(GTK_GRID(grid), entrada_pass2, 1, 2, 1, 1);"""


def main():
    pares = [
        (ANCLA_HELPER, NUEVO_HELPER, "funciones auxiliares del icono de ojo"),
        (ANCLA_1, NUEVO_1, "campo 1/9: entrada_pass (Registrar Colaborador)"),
        (ANCLA_2, NUEVO_2, "campo 2/9: e_gmail_pass (Configurar Notificaciones)"),
        (ANCLA_3, NUEVO_3, "campo 3/9: e_green_token (Configurar Notificaciones)"),
        (ANCLA_4, NUEVO_4, "campo 4/9: e_password (Cliente: Editar mi cuenta)"),
        (ANCLA_5, NUEVO_5, "campo 5/9: e_password (Cliente: Crear cuenta)"),
        (ANCLA_6, NUEVO_6, "campo 6/9: entrada_password (Login de Clientes)"),
        (ANCLA_7, NUEVO_7, "campo 7/9: entrada_password (Login de Colaborador)"),
        (ANCLA_8, NUEVO_8, "campo 8/9: entrada_pass (Crear Administrador)"),
        (ANCLA_9, NUEVO_9, "campo 9/9: entrada_pass2 (Crear Administrador, confirmar)"),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak10")
    print(f"Backup creado: {ARCHIVO}.bak10")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: 9 campos de contrasena con icono de ojo.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
