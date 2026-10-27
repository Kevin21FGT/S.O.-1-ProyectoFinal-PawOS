#!/usr/bin/env python3
"""
parche-portal-editar-foto.py   (despues de parche-portal-foto-registro.py)

Portal de Clientes, pestana "Mi perfil": boton nuevo "Editar foto" debajo de
"Cambiar foto". Abre la foto que YA esta guardada en el editor (girar,
voltear, brillo, contraste) y luego el recorte; al confirmar la reemplaza.
Si todavia no hay foto, avisa que use "Cambiar foto".

Uso (parado en la raiz del repo):
    python3 parche-portal-editar-foto.py
    make portal-clientes && ./pawos-portal-clientes
"""

import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"
MARCA = "on_editar_foto_clicked"

ANCLA_FUNC = "/* ---------- Editar mi perfil ---------- */"
NUEVO_FUNC = r"""/* Editar la foto de perfil que ya esta guardada (sin elegir otro archivo). */
static void on_editar_foto_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;
    GtkWindow *padre = GTK_WINDOW(ctx->ventana);

    char *b64_actual = NULL;
    if (cliente_obtener_foto(ctx->cliente.id, &b64_actual) != 0 || !b64_actual || !b64_actual[0]) {
        free(b64_actual);
        mostrar_mensaje(padre, "Aun no tienes foto. Usa \"Cambiar foto\" para elegir una.", TRUE);
        return;
    }
    gsize largo = 0;
    guchar *bytes = g_base64_decode(b64_actual, &largo);
    free(b64_actual);

    GdkPixbuf *base = NULL;
    if (bytes && largo > 0) {
        GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
        if (gdk_pixbuf_loader_write(loader, bytes, largo, NULL) &&
            gdk_pixbuf_loader_close(loader, NULL)) {
            GdkPixbuf *pix = gdk_pixbuf_loader_get_pixbuf(loader);
            if (pix) base = gdk_pixbuf_copy(pix);
        }
        g_object_unref(loader);
    }
    g_free(bytes);
    if (!base) {
        mostrar_mensaje(padre, "No se pudo leer tu foto actual.", TRUE);
        return;
    }
    if (gdk_pixbuf_get_has_alpha(base)) {
        GdkPixbuf *plano = gdk_pixbuf_composite_color_simple(base,
            gdk_pixbuf_get_width(base), gdk_pixbuf_get_height(base),
            GDK_INTERP_NEAREST, 255, 1, 0xFFFFFF, 0xFFFFFF);
        g_object_unref(base);
        base = plano;
        if (!base) return;
    }

    GdkPixbuf *editada = foto_editor_basico(padre, base);
    g_object_unref(base);
    if (!editada) return;

    GdkPixbuf *recortada = mostrar_dialogo_recorte(padre, editada);
    g_object_unref(editada);
    if (!recortada) return;

    int rw = gdk_pixbuf_get_width(recortada), rh = gdk_pixbuf_get_height(recortada);
    if (rw > 512 || rh > 512) {
        double esc = 512.0 / (double)(rw > rh ? rw : rh);
        GdkPixbuf *mas_chica = gdk_pixbuf_scale_simple(recortada, (int)(rw * esc), (int)(rh * esc), GDK_INTERP_BILINEAR);
        g_object_unref(recortada);
        recortada = mas_chica;
        if (!recortada) return;
    }

    gchar *buffer = NULL;
    gsize tam_buffer = 0;
    GError *error = NULL;
    if (!gdk_pixbuf_save_to_buffer(recortada, &buffer, &tam_buffer, "png", &error, NULL)) {
        mostrar_mensaje(padre, "No se pudo procesar la imagen.", TRUE);
        if (error) g_error_free(error);
        g_object_unref(recortada);
        return;
    }
    g_object_unref(recortada);
    gchar *b64 = g_base64_encode((const guchar *)buffer, tam_buffer);
    g_free(buffer);

    int ok = cliente_guardar_foto(ctx->cliente.id, b64);
    g_free(b64);
    if (ok != 0) {
        mostrar_mensaje(padre, "No se pudo guardar la foto en el servidor.", TRUE);
        return;
    }
    cargar_avatar(ctx);
    mostrar_mensaje(padre, "Foto de perfil actualizada.", FALSE);
}

/* ---------- Editar mi perfil ---------- */"""

ANCLA_BTN = "    gtk_box_pack_start(GTK_BOX(caja_avatar), btn_cambiar_foto, FALSE, FALSE, 0);"
NUEVO_BTN = """    gtk_box_pack_start(GTK_BOX(caja_avatar), btn_cambiar_foto, FALSE, FALSE, 0);
    GtkWidget *btn_editar_foto = gtk_button_new_with_label("Editar foto");
    g_signal_connect(btn_editar_foto, "clicked", G_CALLBACK(on_editar_foto_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(caja_avatar), btn_editar_foto, FALSE, FALSE, 0);"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "seccion Editar mi perfil"),
    (ANCLA_BTN, NUEVO_BTN, "boton Cambiar foto"),
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

    if "foto_editor_basico" not in contenido:
        print("ERROR: falta el editor de fotos. Aplica primero parche-portal-foto-registro.py.")
        sys.exit(1)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_editar_foto")
    print(f"Backup: {ARCHIVO}.bak_editar_foto")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
