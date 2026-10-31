#!/usr/bin/env python3
"""
parche-portal-foto-registro.py

Portal de Clientes:
  1) El cuadro "Registrarme como cliente" ahora tiene "Foto (opcional)" con
     vista previa y botones "Elegir foto..." / "Quitar".
  2) Al elegir una foto (en el registro Y en "Cambiar foto" de Mi perfil) se
     abre un EDITOR BASICO: girar izquierda/derecha, voltear, brillo y
     contraste (con "Restablecer"), y luego el recorte libre de siempre.
  3) Si se eligio foto al registrarse, se guarda en cuanto se crea la cuenta.

No se quita nada: el recorte y el guardado en la BD son los mismos de antes.

Uso (parado en la raiz del repo):
    python3 parche-portal-foto-registro.py
    make portal-clientes && ./pawos-portal-clientes
"""

import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"
MARCA = "portal_obtener_foto_b64"

# ---------------------------------------------------------------- 1) declaracion adelantada
ANCLA_DECL = """static void solo_digitos(const char *src, char *dst, size_t n);
"""
NUEVO_DECL = """static void solo_digitos(const char *src, char *dst, size_t n);
static gchar *portal_obtener_foto_b64(GtkWindow *padre);
"""

# ---------------------------------------------------------------- 2) ayudantes del registro
ANCLA_REG = """static void mostrar_registro(GtkWindow *padre) {"""
NUEVO_REG = r"""/* Convierte una foto base64 en miniatura (conserva proporcion, maximo `lado`). */
static GdkPixbuf *pixbuf_desde_b64(const gchar *b64, int lado) {
    if (!b64 || !b64[0]) return NULL;
    gsize largo = 0;
    guchar *datos = g_base64_decode(b64, &largo);
    if (!datos || largo == 0) { g_free(datos); return NULL; }
    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    GdkPixbuf *res = NULL;
    if (gdk_pixbuf_loader_write(loader, datos, largo, NULL) &&
        gdk_pixbuf_loader_close(loader, NULL)) {
        GdkPixbuf *pix = gdk_pixbuf_loader_get_pixbuf(loader);
        if (pix) {
            int w = gdk_pixbuf_get_width(pix), h = gdk_pixbuf_get_height(pix);
            int mx = w > h ? w : h;
            double f = mx > lado ? (double)lado / (double)mx : 1.0;
            int nw = (int)(w * f), nh = (int)(h * f);
            if (nw < 1) nw = 1;
            if (nh < 1) nh = 1;
            res = gdk_pixbuf_scale_simple(pix, nw, nh, GDK_INTERP_BILINEAR);
        }
    }
    g_object_unref(loader);
    g_free(datos);
    return res;
}

typedef struct {
    GtkWindow *padre;
    GtkWidget *imagen;
    gchar     *b64;
} RegFoto;

static void reg_foto_vaciar(RegFoto *rf) {
    g_free(rf->b64);
    rf->b64 = NULL;
    gtk_image_set_from_icon_name(GTK_IMAGE(rf->imagen), "avatar-default-symbolic", GTK_ICON_SIZE_DIALOG);
}

static void on_reg_foto_elegir(GtkButton *btn, gpointer datos) {
    (void)btn;
    RegFoto *rf = datos;
    gchar *b64 = portal_obtener_foto_b64(rf->padre);
    if (!b64) return;
    g_free(rf->b64);
    rf->b64 = b64;
    GdkPixbuf *mini = pixbuf_desde_b64(b64, 96);
    if (mini) {
        gtk_image_set_from_pixbuf(GTK_IMAGE(rf->imagen), mini);
        g_object_unref(mini);
    }
}

static void on_reg_foto_quitar(GtkButton *btn, gpointer datos) {
    (void)btn;
    reg_foto_vaciar((RegFoto *)datos);
}

static void mostrar_registro(GtkWindow *padre) {"""

# ---------------------------------------------------------------- 3) fila de foto en el formulario
ANCLA_FILA = """    GtkWidget *lbl_nota = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_nota), "<span size='small' foreground='#777777'>* Campo obligatorio</span>");"""
NUEVO_FILA = """    RegFoto rf = { GTK_WINDOW(dialogo), NULL, NULL };
    rf.imagen = gtk_image_new_from_icon_name("avatar-default-symbolic", GTK_ICON_SIZE_DIALOG);
    gtk_image_set_pixel_size(GTK_IMAGE(rf.imagen), 64);
    GtkWidget *caja_foto = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    GtkWidget *col_btn = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    GtkWidget *btn_foto = gtk_button_new_with_label("Elegir foto...");
    GtkWidget *btn_foto_q = gtk_button_new_with_label("Quitar");
    g_signal_connect(btn_foto, "clicked", G_CALLBACK(on_reg_foto_elegir), &rf);
    g_signal_connect(btn_foto_q, "clicked", G_CALLBACK(on_reg_foto_quitar), &rf);
    gtk_box_pack_start(GTK_BOX(col_btn), btn_foto, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(col_btn), btn_foto_q, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_foto), rf.imagen, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_foto), col_btn, FALSE, FALSE, 0);
    GtkWidget *lbl_foto_t = gtk_label_new("Foto (opcional):");
    gtk_widget_set_halign(lbl_foto_t, GTK_ALIGN_START);
    gtk_widget_set_valign(lbl_foto_t, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lbl_foto_t, 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), caja_foto, 1, fila++, 1, 1);

    GtkWidget *lbl_nota = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_nota), "<span size='small' foreground='#777777'>* Campo obligatorio</span>");"""

# ---------------------------------------------------------------- 4) guardar la foto tras registrar
ANCLA_OK = """        mostrar_mensaje(GTK_WINDOW(dialogo), "Registro completado. Ya puedes iniciar sesion.", FALSE);"""
NUEVO_OK = """        if (rf.b64) {
            Cliente nuevo;
            if (cliente_autenticar(correo, pass, &nuevo) == 0)
                cliente_guardar_foto(nuevo.id, rf.b64);
        }
        mostrar_mensaje(GTK_WINDOW(dialogo), "Registro completado. Ya puedes iniciar sesion.", FALSE);"""

# ---------------------------------------------------------------- 5) liberar al cerrar
ANCLA_FIN = """    gtk_widget_destroy(dialogo);
}

/* ---------- Olvide mi contrasena"""
NUEVO_FIN = """    g_free(rf.b64);
    gtk_widget_destroy(dialogo);
}

/* ---------- Olvide mi contrasena"""

CAMBIOS = [
    (ANCLA_DECL, NUEVO_DECL, "declaracion adelantada"),
    (ANCLA_REG, NUEVO_REG, "inicio de mostrar_registro"),
    (ANCLA_FILA, NUEVO_FILA, "nota de campo obligatorio"),
    (ANCLA_OK, NUEVO_OK, "mensaje de registro completado"),
    (ANCLA_FIN, NUEVO_FIN, "cierre de mostrar_registro"),
]

# ---------------------------------------------------------------- 6) editor + flujo de foto (reemplaza on_cambiar_foto_clicked)
INICIO_VIEJO = "static void on_cambiar_foto_clicked(GtkButton *btn, gpointer datos) {"
FIN_VIEJO = "/* ---------- Editar mi perfil ---------- */"

NUEVO_BLOQUE = r"""/* ---------- Editor basico de foto: girar, voltear, brillo, contraste ---------- */

typedef struct {
    GdkPixbuf *base;
    GtkWidget *imagen;
    GtkWidget *esc_brillo;
    GtkWidget *esc_contraste;
} EditorBasico;

static GdkPixbuf *foto_ajustar(GdkPixbuf *src, double brillo, double contraste) {
    GdkPixbuf *dst = gdk_pixbuf_copy(src);
    if (!dst) return NULL;
    if (brillo == 0.0 && contraste == 1.0) return dst;
    guchar tabla[256];
    for (int i = 0; i < 256; i++) {
        double v = (i - 128) * contraste + 128 + brillo;
        tabla[i] = v < 0 ? 0 : (v > 255 ? 255 : (guchar)v);
    }
    int w = gdk_pixbuf_get_width(dst), h = gdk_pixbuf_get_height(dst);
    int nc = gdk_pixbuf_get_n_channels(dst), rs = gdk_pixbuf_get_rowstride(dst);
    guchar *px = gdk_pixbuf_get_pixels(dst);
    for (int y = 0; y < h; y++) {
        guchar *fila = px + (size_t)y * rs;
        for (int x = 0; x < w; x++)
            for (int c = 0; c < 3; c++)
                fila[x * nc + c] = tabla[fila[x * nc + c]];
    }
    return dst;
}

static void ed_refrescar(EditorBasico *e) {
    int w = gdk_pixbuf_get_width(e->base), h = gdk_pixbuf_get_height(e->base);
    int mx = w > h ? w : h;
    GdkPixbuf *peq;
    if (mx > 360) {
        double f = 360.0 / (double)mx;
        int nw = (int)(w * f), nh = (int)(h * f);
        if (nw < 1) nw = 1;
        if (nh < 1) nh = 1;
        peq = gdk_pixbuf_scale_simple(e->base, nw, nh, GDK_INTERP_BILINEAR);
    } else {
        peq = GDK_PIXBUF(g_object_ref(e->base));
    }
    GdkPixbuf *aj = foto_ajustar(peq,
        gtk_range_get_value(GTK_RANGE(e->esc_brillo)),
        gtk_range_get_value(GTK_RANGE(e->esc_contraste)) / 100.0);
    if (aj) {
        gtk_image_set_from_pixbuf(GTK_IMAGE(e->imagen), aj);
        g_object_unref(aj);
    }
    g_object_unref(peq);
}

static void ed_on_slider(GtkRange *r, gpointer datos) {
    (void)r;
    ed_refrescar((EditorBasico *)datos);
}

/* accion: 0 = girar izquierda, 1 = girar derecha, 2 = voltear, 3 = restablecer */
static void ed_on_accion(GtkButton *btn, gpointer datos) {
    EditorBasico *e = datos;
    int accion = GPOINTER_TO_INT(g_object_get_data(G_OBJECT(btn), "accion"));
    GdkPixbuf *nuevo = NULL;
    if (accion == 0)
        nuevo = gdk_pixbuf_rotate_simple(e->base, GDK_PIXBUF_ROTATE_COUNTERCLOCKWISE);
    else if (accion == 1)
        nuevo = gdk_pixbuf_rotate_simple(e->base, GDK_PIXBUF_ROTATE_CLOCKWISE);
    else if (accion == 2)
        nuevo = gdk_pixbuf_flip(e->base, TRUE);
    else {
        gtk_range_set_value(GTK_RANGE(e->esc_brillo), 0);
        gtk_range_set_value(GTK_RANGE(e->esc_contraste), 100);
        return;
    }
    if (nuevo) {
        g_object_unref(e->base);
        e->base = nuevo;
        ed_refrescar(e);
    }
}

static GtkWidget *ed_boton(const char *texto, int accion, EditorBasico *e) {
    GtkWidget *b = gtk_button_new_with_label(texto);
    g_object_set_data(G_OBJECT(b), "accion", GINT_TO_POINTER(accion));
    g_signal_connect(b, "clicked", G_CALLBACK(ed_on_accion), e);
    return b;
}

/* Devuelve un pixbuf nuevo ya editado, o NULL si se cancela. No toma
 * posesion de `original`. */
static GdkPixbuf *foto_editor_basico(GtkWindow *padre, GdkPixbuf *original) {
    EditorBasico e;
    e.base = GDK_PIXBUF(g_object_ref(original));

    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Editar foto", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Continuar al recorte", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 12);
    gtk_box_set_spacing(GTK_BOX(area), 8);

    e.imagen = gtk_image_new();
    gtk_widget_set_size_request(e.imagen, 380, 380);
    gtk_box_pack_start(GTK_BOX(area), e.imagen, TRUE, TRUE, 0);

    GtkWidget *fila_btn = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start(GTK_BOX(fila_btn), ed_boton("Girar a la izquierda", 0, &e), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_btn), ed_boton("Girar a la derecha", 1, &e), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_btn), ed_boton("Voltear", 2, &e), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_btn), ed_boton("Restablecer", 3, &e), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(area), fila_btn, FALSE, FALSE, 0);

    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    e.esc_brillo = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, -100, 100, 1);
    e.esc_contraste = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 50, 200, 1);
    gtk_range_set_value(GTK_RANGE(e.esc_brillo), 0);
    gtk_range_set_value(GTK_RANGE(e.esc_contraste), 100);
    gtk_widget_set_hexpand(e.esc_brillo, TRUE);
    gtk_widget_set_hexpand(e.esc_contraste, TRUE);
    GtkWidget *l1 = gtk_label_new("Brillo:");
    GtkWidget *l2 = gtk_label_new("Contraste:");
    gtk_widget_set_halign(l1, GTK_ALIGN_START);
    gtk_widget_set_halign(l2, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), l1, 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e.esc_brillo, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), l2, 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), e.esc_contraste, 1, 1, 1, 1);
    gtk_box_pack_start(GTK_BOX(area), grid, FALSE, FALSE, 0);
    g_signal_connect(e.esc_brillo, "value-changed", G_CALLBACK(ed_on_slider), &e);
    g_signal_connect(e.esc_contraste, "value-changed", G_CALLBACK(ed_on_slider), &e);

    ed_refrescar(&e);
    gtk_widget_show_all(dialogo);
    int resp = gtk_dialog_run(GTK_DIALOG(dialogo));

    GdkPixbuf *resultado = NULL;
    if (resp == GTK_RESPONSE_OK) {
        resultado = foto_ajustar(e.base,
            gtk_range_get_value(GTK_RANGE(e.esc_brillo)),
            gtk_range_get_value(GTK_RANGE(e.esc_contraste)) / 100.0);
    }
    gtk_widget_destroy(dialogo);
    g_object_unref(e.base);
    return resultado;
}

/* Flujo completo: elegir archivo -> editor basico -> recorte -> PNG en base64.
 * Devuelve una cadena nueva (liberar con g_free) o NULL si se cancela. */
static gchar *portal_obtener_foto_b64(GtkWindow *padre) {
    GtkWidget *selector = gtk_file_chooser_dialog_new("Elegir foto", padre,
        GTK_FILE_CHOOSER_ACTION_OPEN, "_Cancelar", GTK_RESPONSE_CANCEL, "_Abrir", GTK_RESPONSE_ACCEPT, NULL);

    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Imagenes (PNG, JPG)");
    gtk_file_filter_add_mime_type(filtro, "image/png");
    gtk_file_filter_add_mime_type(filtro, "image/jpeg");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(selector), filtro);

    if (gtk_dialog_run(GTK_DIALOG(selector)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(selector);
        return NULL;
    }
    char *ruta = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(selector));
    gtk_widget_destroy(selector);
    if (!ruta) return NULL;

    GError *error = NULL;
    GdkPixbuf *original = gdk_pixbuf_new_from_file(ruta, &error);
    g_free(ruta);
    if (!original) {
        mostrar_mensaje(padre, "No se pudo abrir esa imagen.", TRUE);
        if (error) g_error_free(error);
        return NULL;
    }

    /* Respeta la orientacion del celular, quita transparencia y limita a 1024 px */
    GdkPixbuf *base = gdk_pixbuf_apply_embedded_orientation(original);
    g_object_unref(original);
    if (!base) return NULL;
    if (gdk_pixbuf_get_has_alpha(base)) {
        GdkPixbuf *plano = gdk_pixbuf_composite_color_simple(base,
            gdk_pixbuf_get_width(base), gdk_pixbuf_get_height(base),
            GDK_INTERP_NEAREST, 255, 1, 0xFFFFFF, 0xFFFFFF);
        g_object_unref(base);
        base = plano;
        if (!base) return NULL;
    }
    {
        int w = gdk_pixbuf_get_width(base), h = gdk_pixbuf_get_height(base);
        int mx = w > h ? w : h;
        if (mx > 1024) {
            double f = 1024.0 / (double)mx;
            int nw = (int)(w * f), nh = (int)(h * f);
            if (nw < 1) nw = 1;
            if (nh < 1) nh = 1;
            GdkPixbuf *chica = gdk_pixbuf_scale_simple(base, nw, nh, GDK_INTERP_BILINEAR);
            g_object_unref(base);
            base = chica;
            if (!base) return NULL;
        }
    }

    GdkPixbuf *editada = foto_editor_basico(padre, base);
    g_object_unref(base);
    if (!editada) return NULL;

    GdkPixbuf *recortada = mostrar_dialogo_recorte(padre, editada);
    g_object_unref(editada);
    if (!recortada) return NULL;

    /* Maximo 512 px para no inflar la BD remota */
    int rw = gdk_pixbuf_get_width(recortada), rh = gdk_pixbuf_get_height(recortada);
    if (rw > 512 || rh > 512) {
        double esc = 512.0 / (double)(rw > rh ? rw : rh);
        GdkPixbuf *mas_chica = gdk_pixbuf_scale_simple(recortada, (int)(rw * esc), (int)(rh * esc), GDK_INTERP_BILINEAR);
        g_object_unref(recortada);
        recortada = mas_chica;
        if (!recortada) return NULL;
    }

    gchar *buffer = NULL;
    gsize tam_buffer = 0;
    if (!gdk_pixbuf_save_to_buffer(recortada, &buffer, &tam_buffer, "png", &error, NULL)) {
        mostrar_mensaje(padre, "No se pudo procesar la imagen.", TRUE);
        if (error) g_error_free(error);
        g_object_unref(recortada);
        return NULL;
    }
    g_object_unref(recortada);
    gchar *b64 = g_base64_encode((const guchar *)buffer, tam_buffer);
    g_free(buffer);
    return b64;
}

static void on_cambiar_foto_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    gchar *b64 = portal_obtener_foto_b64(GTK_WINDOW(ctx->ventana));
    if (!b64) return; /* cancelo en algun paso */

    int ok = cliente_guardar_foto(ctx->cliente.id, b64);
    g_free(b64);

    if (ok != 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar la foto en el servidor.", TRUE);
        return;
    }
    cargar_avatar(ctx);
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Foto de perfil actualizada.", FALSE);
}

"""


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
    for marca, nombre in ((INICIO_VIEJO, "on_cambiar_foto_clicked"), (FIN_VIEJO, "seccion Editar mi perfil")):
        n = contenido.count(marca)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)
    i = contenido.index(INICIO_VIEJO)
    j = contenido.index(FIN_VIEJO)
    if j < i:
        print("ERROR: el orden de las secciones no es el esperado. No se cambio nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_foto_registro")
    print(f"Backup: {ARCHIVO}.bak_foto_registro")

    contenido = contenido[:i] + NUEVO_BLOQUE + contenido[j:]
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
