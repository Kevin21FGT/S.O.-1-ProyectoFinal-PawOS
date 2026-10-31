#!/usr/bin/env python3
"""
parche-portal-cerrar-sesion.py

Portal de Clientes: ya no se cierra el programa por accidente.

  - Al cerrar la ventana (la X) con la sesion iniciada sale el mensaje
    "Deseas cerrar sesion y volver al inicio de sesion?" con dos botones:
        [Continuar]      -> sigue en el Portal
        [Cerrar sesion]  -> vuelve a la ventana de login
  - El boton "Cerrar sesion" del perfil tambien vuelve al login (antes
    cerraba todo el programa).
  - El programa solo se cierra con "Salir" en la ventana de login.

Uso (parado en la raiz del repo):
    python3 parche-portal-cerrar-sesion.py
    make portal-clientes && ./pawos-portal-clientes
"""

import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"
MARCA = "on_ventana_delete"

ANCLA_FUNC = r"""static void construir_ventana(ContextoApp *ctx) {"""
NUEVO_FUNC = r"""/* Al cerrar la ventana (X) se pregunta antes: Continuar o Cerrar sesion.
 * Devolver TRUE evita que la ventana se cierre. */
static gboolean on_ventana_delete(GtkWidget *ventana, GdkEvent *evento, gpointer datos) {
    (void)evento;
    (void)datos;
    GtkWidget *d = gtk_message_dialog_new(GTK_WINDOW(ventana), GTK_DIALOG_MODAL,
        GTK_MESSAGE_QUESTION, GTK_BUTTONS_NONE, "%s",
        "Deseas cerrar sesion y volver al inicio de sesion?");
    gtk_message_dialog_format_secondary_text(GTK_MESSAGE_DIALOG(d), "%s",
        "Elige \"Continuar\" para seguir usando el Portal.");
    gtk_dialog_add_button(GTK_DIALOG(d), "Continuar", GTK_RESPONSE_CANCEL);
    gtk_dialog_add_button(GTK_DIALOG(d), "Cerrar sesion", GTK_RESPONSE_OK);
    gtk_dialog_set_default_response(GTK_DIALOG(d), GTK_RESPONSE_CANCEL);
    int r = gtk_dialog_run(GTK_DIALOG(d));
    gtk_widget_destroy(d);
    return r != GTK_RESPONSE_OK;
}

static void construir_ventana(ContextoApp *ctx) {"""

ANCLA_SIGNAL = r"""    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);"""
NUEVO_SIGNAL = r"""    g_signal_connect(ctx->ventana, "delete-event", G_CALLBACK(on_ventana_delete), NULL);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);"""

ANCLA_MAIN = r"""    ContextoApp ctx;
    memset(&ctx, 0, sizeof(ctx));

    if (!mostrar_login(&ctx.cliente)) {
        db_close();
        return 0;
    }

    construir_ventana(&ctx);
    cargar_avatar(&ctx);
    cargar_mis_vacunas(&ctx);

    gtk_main();
    db_close();
    return 0;"""
NUEVO_MAIN = r"""    /* Login -> Portal -> (cerrar sesion) -> Login ... El programa solo se
     * cierra con "Salir" en la ventana de login. */
    for (;;) {
        ContextoApp ctx;
        memset(&ctx, 0, sizeof(ctx));

        if (!mostrar_login(&ctx.cliente)) break;

        construir_ventana(&ctx);
        cargar_avatar(&ctx);
        cargar_mis_vacunas(&ctx);

        gtk_main();   /* vuelve cuando se cierra la sesion */
    }
    db_close();
    return 0;"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de construir_ventana"),
    (ANCLA_SIGNAL, NUEVO_SIGNAL, "senal destroy de la ventana"),
    (ANCLA_MAIN, NUEVO_MAIN, "main"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_cerrar_sesion")
    print(f"Backup: {ARCHIVO}.bak_cerrar_sesion")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
