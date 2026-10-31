#!/usr/bin/env python3
"""
parche-editor-foto-camara.py  (ETAPA 2 de fotos de mascotas)

Reemplaza el selector simple de foto de mascotas (Registrar nueva y boton
Foto -> "Cambiar foto...") por un flujo completo, sin tocar la base de
datos ni lo demas:

  1. Se elige el ORIGEN: "Elegir archivo..." o "Tomar con la camara...".
  2. Camara: vista previa en vivo (ffmpeg + /dev/videoN, sirve la webcam
     de la laptop o DroidCam pasada por VirtualBox) y boton "Tomar foto".
  3. EDITOR: girar izquierda/derecha, voltear, formato (original,
     cuadrada 1:1, horizontal 4:3), zoom y mover el encuadre, brillo y
     contraste, y "Restablecer". Se guarda igual que antes (JPEG 300 px
     en base64 en mascotas.foto_base64).

Requiere ffmpeg (ya instalado) solo para la camara.

Uso (parado en la raiz del repo):
    python3 parche-editor-foto-camara.py
    make gui
"""

import shutil
import sys

GTK_C = "src/main_gtk.c"

# --- 1) include de signal.h (para detener ffmpeg) -------------------------
ANCLA_INC = "#include <errno.h>\n#include \"db/db.h\""
NUEVO_INC = "#include <errno.h>\n#include <signal.h>\n#include \"db/db.h\""

# --- 2) foto_archivo_a_base64 ya no se usa: evitar el aviso ---------------
ANCLA_UNUSED = r"""static gchar *foto_archivo_a_base64(const char *ruta, int max_lado, GdkPixbuf **vista_out) {"""
NUEVO_UNUSED = r"""__attribute__((unused))
static gchar *foto_archivo_a_base64(const char *ruta, int max_lado, GdkPixbuf **vista_out) {"""

# --- 3) helpers nuevos + handler del registro -----------------------------
ANCLA_REG = r"""/* referencias[0] = GtkImage de vista previa, referencias[1] = dialogo padre.
 * La foto reducida (base64) queda como dato "foto_base64" de la imagen. */
static void on_elegir_foto_mascota_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWidget **refs = (GtkWidget **)datos;
    char *ruta = elegir_imagen_ruta(GTK_WINDOW(refs[1]));
    if (!ruta) return;
    GdkPixbuf *vista = NULL;
    gchar *b64 = foto_archivo_a_base64(ruta, 300, &vista);
    g_free(ruta);
    if (!b64) {
        mostrar_mensaje(GTK_WINDOW(refs[1]), "No se pudo leer esa imagen.", TRUE);
        return;
    }"""

NUEVO_REG = r"""/* =================================================================
 * Editor de foto y camara (mascotas)
 * ================================================================= */

/* Carga una imagen: la endereza (EXIF), le quita la transparencia y la
 * reduce a max_lado para poder editarla con fluidez. */
static GdkPixbuf *foto_cargar_archivo(const char *ruta, int max_lado) {
    GdkPixbuf *orig = gdk_pixbuf_new_from_file(ruta, NULL);
    if (!orig) return NULL;
    GdkPixbuf *base = gdk_pixbuf_apply_embedded_orientation(orig);
    g_object_unref(orig);
    if (!base) return NULL;
    if (gdk_pixbuf_get_has_alpha(base)) {
        GdkPixbuf *plano = gdk_pixbuf_composite_color_simple(
            base, gdk_pixbuf_get_width(base), gdk_pixbuf_get_height(base),
            GDK_INTERP_NEAREST, 255, 1, 0xFFFFFF, 0xFFFFFF);
        g_object_unref(base);
        base = plano;
        if (!base) return NULL;
    }
    GdkPixbuf *res = foto_escalar(base, max_lado);
    g_object_unref(base);
    return res;
}

/* ---------- Camara (vista previa en vivo con ffmpeg) ---------- */

typedef struct {
    GtkWidget  *dialogo;
    GtkWidget  *imagen;
    GtkWidget  *etiqueta;
    GtkWidget  *combo;
    GPid        pid;
    gboolean    activo;
    guint       watch;
    guint       timeout;
    GIOChannel *canal;
    GByteArray *buf;
    GdkPixbuf  *ultimo;
} CamaraCtx;

static gint comparar_video(gconstpointer a, gconstpointer b) {
    const char *sa = *(const char * const *)a;
    const char *sb = *(const char * const *)b;
    return atoi(sa + 5) - atoi(sb + 5);
}

static void camara_llenar_combo(GtkWidget *combo) {
    GPtrArray *lista = g_ptr_array_new_with_free_func(g_free);
    GDir *dir = g_dir_open("/dev", 0, NULL);
    if (dir) {
        const char *n;
        while ((n = g_dir_read_name(dir)) != NULL) {
            if (g_str_has_prefix(n, "video") && n[5] >= '0' && n[5] <= '9')
                g_ptr_array_add(lista, g_strdup(n));
        }
        g_dir_close(dir);
    }
    g_ptr_array_sort(lista, comparar_video);
    for (guint i = 0; i < lista->len; i++) {
        gchar *ruta = g_strdup_printf("/dev/%s", (char *)g_ptr_array_index(lista, i));
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), ruta);
        g_free(ruta);
    }
    if (lista->len > 0) gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);
    g_ptr_array_free(lista, TRUE);
}

static void camara_detener(CamaraCtx *c) {
    if (c->watch)   { g_source_remove(c->watch);   c->watch = 0; }
    if (c->timeout) { g_source_remove(c->timeout); c->timeout = 0; }
    if (c->canal) {
        g_io_channel_shutdown(c->canal, FALSE, NULL);
        g_io_channel_unref(c->canal);
        c->canal = NULL;
    }
    if (c->activo) {
        kill((pid_t)c->pid, SIGTERM);
        g_spawn_close_pid(c->pid);
        c->activo = FALSE;
    }
    g_byte_array_set_size(c->buf, 0);
}

static void camara_mostrar_cuadro(CamaraCtx *c, const guint8 *datos, gsize largo) {
    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    if (gdk_pixbuf_loader_write(loader, datos, largo, NULL)) {
        gdk_pixbuf_loader_close(loader, NULL);
        GdkPixbuf *pb = gdk_pixbuf_loader_get_pixbuf(loader);
        if (pb) {
            g_clear_object(&c->ultimo);
            c->ultimo = g_object_ref(pb);
            GdkPixbuf *v = foto_escalar(pb, 480);
            gtk_image_set_from_pixbuf(GTK_IMAGE(c->imagen), v);
            g_object_unref(v);
            gtk_label_set_text(GTK_LABEL(c->etiqueta),
                "Encuadra a la mascota y pulsa \"Tomar foto\".");
        }
    } else {
        gdk_pixbuf_loader_close(loader, NULL);
    }
    g_object_unref(loader);
}

/* Busca cuadros JPEG completos (FFD8 ... FFD9) en lo recibido y muestra el
 * ultimo; lo que sobra se conserva para la proxima lectura. */
static void camara_procesar_buffer(CamaraCtx *c) {
    const guint8 *d = c->buf->data;
    gsize n = c->buf->len;
    gsize i = 0, ult_ini = 0, ult_fin = 0;
    gboolean encontrado = FALSE;
    while (i + 1 < n) {
        if (d[i] == 0xFF && d[i + 1] == 0xD8) {
            gsize j = i + 2;
            gboolean cerrado = FALSE;
            while (j + 1 < n) {
                if (d[j] == 0xFF && d[j + 1] == 0xD9) { cerrado = TRUE; break; }
                j++;
            }
            if (!cerrado) break;
            ult_ini = i;
            ult_fin = j + 2;
            encontrado = TRUE;
            i = j + 2;
        } else {
            i++;
        }
    }
    if (encontrado) camara_mostrar_cuadro(c, d + ult_ini, ult_fin - ult_ini);
    if (i > 0) g_byte_array_remove_range(c->buf, 0, (guint)(i > n ? n : i));
}

static gboolean camara_datos_cb(GIOChannel *canal, GIOCondition cond, gpointer datos) {
    (void)cond;
    CamaraCtx *c = (CamaraCtx *)datos;
    guchar tmp[65536];
    gsize leidos = 0;
    GIOStatus st = g_io_channel_read_chars(canal, (gchar *)tmp, sizeof(tmp), &leidos, NULL);
    if (leidos > 0) {
        g_byte_array_append(c->buf, tmp, (guint)leidos);
        if (c->buf->len > 8u * 1024u * 1024u) g_byte_array_set_size(c->buf, 0);
        camara_procesar_buffer(c);
    }
    if (st == G_IO_STATUS_EOF || st == G_IO_STATUS_ERROR) {
        c->watch = 0;
        if (!c->ultimo)
            gtk_label_set_text(GTK_LABEL(c->etiqueta),
                "Este dispositivo no entrega imagen. Prueba otro de la lista.");
        return FALSE;
    }
    return TRUE;
}

static gboolean camara_sin_imagen_cb(gpointer datos) {
    CamaraCtx *c = (CamaraCtx *)datos;
    c->timeout = 0;
    if (!c->ultimo)
        gtk_label_set_text(GTK_LABEL(c->etiqueta),
            "No llega imagen de este dispositivo. Prueba otro de la lista.");
    return FALSE;
}

static void camara_iniciar(CamaraCtx *c) {
    camara_detener(c);
    g_clear_object(&c->ultimo);
    gchar *dev = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(c->combo));
    if (!dev) {
        gtk_label_set_text(GTK_LABEL(c->etiqueta),
            "No se encontro ninguna camara. En VirtualBox: Dispositivos > Camaras web.");
        return;
    }
    gchar *argv[] = {
        "ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", dev,
        "-vf", "fps=10,scale=960:-2", "-c:v", "mjpeg", "-q:v", "4",
        "-f", "image2pipe", "-", NULL
    };
    gint fd_out = -1;
    GError *err = NULL;
    if (!g_spawn_async_with_pipes(NULL, argv, NULL, G_SPAWN_SEARCH_PATH,
                                  NULL, NULL, &c->pid, NULL, &fd_out, NULL, &err)) {
        gtk_label_set_text(GTK_LABEL(c->etiqueta),
            "No se pudo iniciar ffmpeg (sudo apt install ffmpeg).");
        if (err) g_error_free(err);
        g_free(dev);
        return;
    }
    c->activo = TRUE;
    c->canal = g_io_channel_unix_new(fd_out);
    g_io_channel_set_encoding(c->canal, NULL, NULL);
    g_io_channel_set_flags(c->canal, G_IO_FLAG_NONBLOCK, NULL);
    c->watch = g_io_add_watch(c->canal, G_IO_IN | G_IO_ERR | G_IO_HUP, camara_datos_cb, c);
    c->timeout = g_timeout_add(5000, camara_sin_imagen_cb, c);
    gtk_label_set_text(GTK_LABEL(c->etiqueta), "Conectando con la camara...");
    g_free(dev);
}

static void on_camara_cambiada(GtkComboBox *combo, gpointer datos) {
    (void)combo;
    camara_iniciar((CamaraCtx *)datos);
}

/* Devuelve el cuadro tomado (g_object_unref) o NULL si se cancela. */
static GdkPixbuf *camara_capturar_dialogo(GtkWindow *padre) {
    CamaraCtx c;
    memset(&c, 0, sizeof(c));
    c.buf = g_byte_array_new();

    c.dialogo = gtk_dialog_new_with_buttons(
        "Tomar foto con la camara", padre, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Tomar foto", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(c.dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    GtkWidget *fila = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(fila), gtk_label_new("Camara:"), FALSE, FALSE, 0);
    c.combo = gtk_combo_box_text_new();
    camara_llenar_combo(c.combo);
    gtk_box_pack_start(GTK_BOX(fila), c.combo, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(caja), fila, FALSE, FALSE, 0);

    c.imagen = gtk_image_new_from_icon_name("camera-video", GTK_ICON_SIZE_DIALOG);
    gtk_widget_set_size_request(c.imagen, 480, 270);
    gtk_box_pack_start(GTK_BOX(caja), c.imagen, TRUE, TRUE, 0);
    c.etiqueta = gtk_label_new("");
    gtk_box_pack_start(GTK_BOX(caja), c.etiqueta, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);
    mostrar_con_fundido(c.dialogo);

    g_signal_connect(c.combo, "changed", G_CALLBACK(on_camara_cambiada), &c);
    camara_iniciar(&c);

    GdkPixbuf *resultado = NULL;
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(c.dialogo)) != GTK_RESPONSE_OK) break;
        if (!c.ultimo) {
            mostrar_mensaje(GTK_WINDOW(c.dialogo), "Todavia no hay imagen de la camara.", TRUE);
            continue;
        }
        resultado = g_object_ref(c.ultimo);
        break;
    }
    camara_detener(&c);
    gtk_widget_destroy(c.dialogo);
    g_clear_object(&c.ultimo);
    g_byte_array_free(c.buf, TRUE);
    return resultado;
}

/* ---------- Editor de foto ---------- */

typedef struct {
    GdkPixbuf *origen;
    GtkWidget *imagen;
    GtkWidget *combo;
    GtkWidget *zoom;
    GtkWidget *mx;
    GtkWidget *my;
    GtkWidget *brillo;
    GtkWidget *contraste;
    int        rot;      /* cuartos de vuelta a la derecha: 0..3 */
    gboolean   volteo;
} EditorFoto;

/* Aplica giro/volteo, recorte (formato + zoom + posicion) y brillo/contraste.
 * formato: 0 original, 1 cuadrada 1:1, 2 horizontal 4:3. */
static GdkPixbuf *foto_procesar(GdkPixbuf *src, int rot, gboolean volteo, int formato,
                                double zoom, double px, double py,
                                double brillo, double contraste, int max_lado) {
    GdkPixbuf *a = g_object_ref(src);
    for (int k = 0; k < rot; k++) {
        GdkPixbuf *t = gdk_pixbuf_rotate_simple(a, GDK_PIXBUF_ROTATE_CLOCKWISE);
        g_object_unref(a);
        a = t;
        if (!a) return NULL;
    }
    if (volteo) {
        GdkPixbuf *t = gdk_pixbuf_flip(a, TRUE);
        g_object_unref(a);
        a = t;
        if (!a) return NULL;
    }
    int w = gdk_pixbuf_get_width(a), h = gdk_pixbuf_get_height(a);
    double ar = (formato == 1) ? 1.0 : (formato == 2) ? (4.0 / 3.0) : ((double)w / (double)h);
    double cw, ch;
    if ((double)w / (double)h > ar) { ch = h; cw = h * ar; }
    else                            { cw = w; ch = w / ar; }
    if (zoom < 1.0) zoom = 1.0;
    cw /= zoom;
    ch /= zoom;
    int icw = (int)cw, ich = (int)ch;
    if (icw < 1) icw = 1;
    if (ich < 1) ich = 1;
    if (icw > w) icw = w;
    if (ich > h) ich = h;
    int ix = (int)((w - icw) * px / 100.0);
    int iy = (int)((h - ich) * py / 100.0);
    if (ix < 0) ix = 0;
    if (iy < 0) iy = 0;
    if (ix > w - icw) ix = w - icw;
    if (iy > h - ich) iy = h - ich;

    GdkPixbuf *sub = gdk_pixbuf_new_subpixbuf(a, ix, iy, icw, ich);
    GdkPixbuf *esc = foto_escalar(sub, max_lado);
    GdkPixbuf *out = gdk_pixbuf_copy(esc);
    g_object_unref(esc);
    g_object_unref(sub);
    g_object_unref(a);
    if (!out) return NULL;

    if (brillo > 0.5 || brillo < -0.5 || contraste > 1.01 || contraste < 0.99) {
        int nch = gdk_pixbuf_get_n_channels(out);
        int rs = gdk_pixbuf_get_rowstride(out);
        int ow = gdk_pixbuf_get_width(out), oh = gdk_pixbuf_get_height(out);
        guchar *pix = gdk_pixbuf_get_pixels(out);
        for (int y = 0; y < oh; y++) {
            guchar *fila = pix + (gsize)y * (gsize)rs;
            for (int x = 0; x < ow; x++) {
                for (int cc = 0; cc < 3; cc++) {
                    double v = ((double)fila[x * nch + cc] - 128.0) * contraste + 128.0 + brillo;
                    if (v < 0.0) v = 0.0;
                    if (v > 255.0) v = 255.0;
                    fila[x * nch + cc] = (guchar)v;
                }
            }
        }
    }
    return out;
}

static GdkPixbuf *editor_generar(EditorFoto *e, int max_lado) {
    return foto_procesar(e->origen, e->rot, e->volteo,
        gtk_combo_box_get_active(GTK_COMBO_BOX(e->combo)),
        gtk_range_get_value(GTK_RANGE(e->zoom)),
        gtk_range_get_value(GTK_RANGE(e->mx)),
        gtk_range_get_value(GTK_RANGE(e->my)),
        gtk_range_get_value(GTK_RANGE(e->brillo)),
        gtk_range_get_value(GTK_RANGE(e->contraste)),
        max_lado);
}

static void editor_actualizar(EditorFoto *e) {
    GdkPixbuf *p = editor_generar(e, 360);
    if (p) {
        gtk_image_set_from_pixbuf(GTK_IMAGE(e->imagen), p);
        g_object_unref(p);
    }
}

static void on_editor_cambio(GtkWidget *w, gpointer datos) {
    (void)w;
    editor_actualizar((EditorFoto *)datos);
}

static void on_editor_rotar_izq(GtkButton *b, gpointer datos) {
    (void)b;
    EditorFoto *e = (EditorFoto *)datos;
    e->rot = (e->rot + 3) % 4;
    editor_actualizar(e);
}

static void on_editor_rotar_der(GtkButton *b, gpointer datos) {
    (void)b;
    EditorFoto *e = (EditorFoto *)datos;
    e->rot = (e->rot + 1) % 4;
    editor_actualizar(e);
}

static void on_editor_voltear(GtkButton *b, gpointer datos) {
    (void)b;
    EditorFoto *e = (EditorFoto *)datos;
    e->volteo = !e->volteo;
    editor_actualizar(e);
}

static void on_editor_reset(GtkButton *b, gpointer datos) {
    (void)b;
    EditorFoto *e = (EditorFoto *)datos;
    e->rot = 0;
    e->volteo = FALSE;
    gtk_combo_box_set_active(GTK_COMBO_BOX(e->combo), 0);
    gtk_range_set_value(GTK_RANGE(e->zoom), 1.0);
    gtk_range_set_value(GTK_RANGE(e->mx), 50.0);
    gtk_range_set_value(GTK_RANGE(e->my), 50.0);
    gtk_range_set_value(GTK_RANGE(e->brillo), 0.0);
    gtk_range_set_value(GTK_RANGE(e->contraste), 1.0);
    editor_actualizar(e);
}

/* Editor modal. Devuelve la foto final (JPEG 300 px) en base64 (g_free) o
 * NULL si se cancela. vista_out: copia en pixbuf para la vista previa. */
static gchar *foto_editor_dialogo(GtkWindow *padre, GdkPixbuf *origen, GdkPixbuf **vista_out) {
    if (vista_out) *vista_out = NULL;
    EditorFoto e;
    memset(&e, 0, sizeof(e));
    e.origen = origen;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar foto", padre, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Usar esta foto", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 14);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);

    e.imagen = gtk_image_new();
    gtk_widget_set_size_request(e.imagen, 380, 380);
    gtk_box_pack_start(GTK_BOX(caja), e.imagen, FALSE, FALSE, 0);

    GtkWidget *panel = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_box_pack_start(GTK_BOX(caja), panel, TRUE, TRUE, 0);

    GtkWidget *fila_btn = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *btn_izq = gtk_button_new_with_label("Girar izquierda");
    GtkWidget *btn_der = gtk_button_new_with_label("Girar derecha");
    GtkWidget *btn_vol = gtk_button_new_with_label("Voltear");
    gtk_box_pack_start(GTK_BOX(fila_btn), btn_izq, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_btn), btn_der, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_btn), btn_vol, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(panel), fila_btn, FALSE, FALSE, 0);

    GtkWidget *cuad = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(cuad), 6);
    gtk_grid_set_column_spacing(GTK_GRID(cuad), 10);

    e.combo = gtk_combo_box_text_new();
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(e.combo), "Original");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(e.combo), "Cuadrada (1:1)");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(e.combo), "Horizontal (4:3)");
    gtk_combo_box_set_active(GTK_COMBO_BOX(e.combo), 0);

    e.zoom      = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 1.0, 3.0, 0.05);
    e.mx        = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.0, 100.0, 1.0);
    e.my        = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.0, 100.0, 1.0);
    e.brillo    = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, -80.0, 80.0, 1.0);
    e.contraste = gtk_scale_new_with_range(GTK_ORIENTATION_HORIZONTAL, 0.5, 1.5, 0.05);
    gtk_range_set_value(GTK_RANGE(e.zoom), 1.0);
    gtk_range_set_value(GTK_RANGE(e.mx), 50.0);
    gtk_range_set_value(GTK_RANGE(e.my), 50.0);
    gtk_range_set_value(GTK_RANGE(e.brillo), 0.0);
    gtk_range_set_value(GTK_RANGE(e.contraste), 1.0);
    gtk_scale_set_digits(GTK_SCALE(e.zoom), 2);
    gtk_scale_set_digits(GTK_SCALE(e.mx), 0);
    gtk_scale_set_digits(GTK_SCALE(e.my), 0);
    gtk_scale_set_digits(GTK_SCALE(e.brillo), 0);
    gtk_scale_set_digits(GTK_SCALE(e.contraste), 2);
    gtk_widget_set_size_request(e.zoom, 240, -1);
    gtk_widget_set_hexpand(e.zoom, TRUE);
    gtk_widget_set_hexpand(e.mx, TRUE);
    gtk_widget_set_hexpand(e.my, TRUE);
    gtk_widget_set_hexpand(e.brillo, TRUE);
    gtk_widget_set_hexpand(e.contraste, TRUE);

    const char *nombres[6] = {"Formato:", "Zoom:", "Mover horizontal:", "Mover vertical:", "Brillo:", "Contraste:"};
    GtkWidget *controles[6] = {e.combo, e.zoom, e.mx, e.my, e.brillo, e.contraste};
    for (int i = 0; i < 6; i++) {
        GtkWidget *lbl = gtk_label_new(nombres[i]);
        gtk_widget_set_halign(lbl, GTK_ALIGN_END);
        gtk_grid_attach(GTK_GRID(cuad), lbl, 0, i, 1, 1);
        gtk_grid_attach(GTK_GRID(cuad), controles[i], 1, i, 1, 1);
    }
    gtk_box_pack_start(GTK_BOX(panel), cuad, FALSE, FALSE, 0);

    GtkWidget *btn_reset = gtk_button_new_with_label("Restablecer");
    gtk_box_pack_start(GTK_BOX(panel), btn_reset, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);

    /* Las senales se conectan al final: asi ninguna dispara antes de que
     * existan todos los controles. */
    g_signal_connect(btn_izq, "clicked", G_CALLBACK(on_editor_rotar_izq), &e);
    g_signal_connect(btn_der, "clicked", G_CALLBACK(on_editor_rotar_der), &e);
    g_signal_connect(btn_vol, "clicked", G_CALLBACK(on_editor_voltear), &e);
    g_signal_connect(btn_reset, "clicked", G_CALLBACK(on_editor_reset), &e);
    g_signal_connect(e.combo, "changed", G_CALLBACK(on_editor_cambio), &e);
    g_signal_connect(e.zoom, "value-changed", G_CALLBACK(on_editor_cambio), &e);
    g_signal_connect(e.mx, "value-changed", G_CALLBACK(on_editor_cambio), &e);
    g_signal_connect(e.my, "value-changed", G_CALLBACK(on_editor_cambio), &e);
    g_signal_connect(e.brillo, "value-changed", G_CALLBACK(on_editor_cambio), &e);
    g_signal_connect(e.contraste, "value-changed", G_CALLBACK(on_editor_cambio), &e);

    mostrar_con_fundido(dialogo);
    editor_actualizar(&e);

    gchar *b64 = NULL;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        GdkPixbuf *fin = editor_generar(&e, 300);
        if (fin) {
            gchar *buf = NULL;
            gsize largo = 0;
            if (gdk_pixbuf_save_to_buffer(fin, &buf, &largo, "jpeg", NULL, "quality", "85", NULL)) {
                b64 = g_base64_encode((const guchar *)buf, largo);
                g_free(buf);
                if (vista_out) *vista_out = g_object_ref(fin);
            }
            g_object_unref(fin);
        }
    }
    gtk_widget_destroy(dialogo);
    return b64;
}

/* Flujo completo: elegir origen (archivo o camara) y editar. Devuelve el
 * base64 listo para guardar (g_free) o NULL si se cancela. */
static gchar *obtener_foto_mascota(GtkWindow *padre, GdkPixbuf **vista_out) {
    if (vista_out) *vista_out = NULL;
    GtkWidget *dlg = gtk_dialog_new_with_buttons(
        "Foto de la mascota", padre, GTK_DIALOG_MODAL,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Elegir archivo...", 1,
        "Tomar con la camara...", 2, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dlg));
    GtkWidget *lbl = gtk_label_new("De donde quieres tomar la foto?");
    gtk_container_set_border_width(GTK_CONTAINER(lbl), 18);
    gtk_container_add(GTK_CONTAINER(area), lbl);
    mostrar_con_fundido(dlg);
    int r = gtk_dialog_run(GTK_DIALOG(dlg));
    gtk_widget_destroy(dlg);

    GdkPixbuf *origen = NULL;
    if (r == 1) {
        char *ruta = elegir_imagen_ruta(padre);
        if (!ruta) return NULL;
        origen = foto_cargar_archivo(ruta, 1600);
        g_free(ruta);
        if (!origen) {
            mostrar_mensaje(padre, "No se pudo leer esa imagen.", TRUE);
            return NULL;
        }
    } else if (r == 2) {
        GdkPixbuf *cam = camara_capturar_dialogo(padre);
        if (!cam) return NULL;
        origen = foto_escalar(cam, 1600);
        g_object_unref(cam);
    } else {
        return NULL;
    }
    gchar *b64 = foto_editor_dialogo(padre, origen, vista_out);
    g_object_unref(origen);
    return b64;
}

/* referencias[0] = GtkImage de vista previa, referencias[1] = dialogo padre.
 * La foto reducida (base64) queda como dato "foto_base64" de la imagen. */
static void on_elegir_foto_mascota_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    GtkWidget **refs = (GtkWidget **)datos;
    GdkPixbuf *vista = NULL;
    gchar *b64 = obtener_foto_mascota(GTK_WINDOW(refs[1]), &vista);
    if (!b64) return;"""

# --- 4) boton Foto -> "Cambiar foto..." -----------------------------------
ANCLA_CAMBIAR = r"""        char *ruta = elegir_imagen_ruta(GTK_WINDOW(dialogo));
        if (!ruta) continue;
        gchar *b64 = foto_archivo_a_base64(ruta, 300, NULL);
        g_free(ruta);
        if (!b64) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo leer esa imagen.", TRUE);
            continue;
        }"""
NUEVO_CAMBIAR = r"""        gchar *b64 = obtener_foto_mascota(GTK_WINDOW(dialogo), NULL);
        if (!b64) continue;"""

CAMBIOS = [
    (ANCLA_INC, NUEVO_INC, "include errno/db.h"),
    (ANCLA_UNUSED, NUEVO_UNUSED, "foto_archivo_a_base64"),
    (ANCLA_REG, NUEVO_REG, "on_elegir_foto_mascota_clicked"),
    (ANCLA_CAMBIAR, NUEVO_CAMBIAR, "cambiar foto del boton Foto"),
]


def main():
    try:
        with open(GTK_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "camara_capturar_dialogo" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            print("       Verifica que ya aplicaste parche-foto-mascotas.py.")
            sys.exit(1)

    shutil.copy(GTK_C, GTK_C + ".bak_editor_foto")
    print(f"Backup: {GTK_C}.bak_editor_foto")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(GTK_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{GTK_C} parchado OK.")
    print("")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")
    print("Prueba: Gestion de Mascotas -> Foto -> Cambiar foto... (o Registrar nueva).")


if __name__ == "__main__":
    main()
