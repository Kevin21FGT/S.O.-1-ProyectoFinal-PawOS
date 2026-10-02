/*
 * main_portal_clientes.c - PawOS Portal de Clientes
 *
 * App grafica standalone (GTK3) para que los Clientes (adoptantes y
 * donantes externos, tabla "clientes") inicien sesion y vean su
 * propia informacion, sin acceso a la administracion del refugio
 * (eso sigue siendo exclusivo de PawOS Refugio GUI / CLI).
 *
 * Reutiliza por completo la logica ya existente en db.c:
 * cliente_autenticar, cliente_registrar, cliente_existe,
 * cliente_actualizar, cliente_rol_nombre, cliente_guardar_foto,
 * cliente_obtener_foto, vacuna_listar, mascota_buscar_por_id -- no
 * reimplementa nada de negocio.
 *
 * La foto de perfil se guarda como texto base64 (mismo truco que ya
 * usa usuario_registrar para el personal del refugio), en una
 * columna de la tabla "clientes" en el SQL Server remoto. El usuario
 * elige el archivo y luego recorta libremente (tamano personalizado,
 * arrastrando el mouse) la parte que quiere usar.
 */
#include <gtk/gtk.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "db/db.h"
#include "version.h"

#define RUTA_BD_DEFECTO "/var/pawos/pawos.db"
#define RESPUESTA_REGISTRARME 1
#define FOTO_AVATAR_SIZE 84
#define RECORTE_MAX_DIM 640

enum {
    COL_V_MASCOTA = 0,
    COL_V_VACUNA,
    COL_V_PROXIMA,
    COL_V_ESTADO,
    COL_V_COLOR,
    N_COLUMNAS_VACUNA
};

typedef struct {
    GtkWidget    *ventana;
    GtkWidget    *imagen_avatar;
    Cliente       cliente;
    GtkListStore *store_vacunas;
} ContextoApp;

static void mostrar_mensaje(GtkWindow *padre, const char *texto, gboolean es_error) {
    GtkWidget *dialogo = gtk_message_dialog_new(padre, GTK_DIALOG_MODAL,
        es_error ? GTK_MESSAGE_ERROR : GTK_MESSAGE_INFO, GTK_BUTTONS_OK, "%s", texto);
    gtk_dialog_run(GTK_DIALOG(dialogo));
    gtk_widget_destroy(dialogo);
}

static void aplicar_estilos_simples(void) {
    GtkCssProvider *proveedor = gtk_css_provider_new();
    const char *css =
        "window { background-color: #F4F6F5; }"
        ".pawos-header {"
        "  background-image: linear-gradient(180deg, #23924B 0%, #12451F 100%);"
        "  padding: 16px 20px;"
        "}"
        ".pawos-header label { color: #FFFFFF; }"
        ".pawos-tarjeta {"
        "  background-color: #FFFFFF;"
        "  border-radius: 12px;"
        "  padding: 16px;"
        "  box-shadow: 0 2px 8px rgba(0,0,0,0.10);"
        "}"
        "button.pawos-accion {"
        "  background-image: none;"
        "  background-color: #23924B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-accion:hover { background-color: #1D7A3E; }"
        "button.pawos-peligro {"
        "  background-image: none;"
        "  background-color: #C0392B;"
        "  color: #FFFFFF;"
        "  border-radius: 8px;"
        "  padding: 6px 14px;"
        "}"
        "button.pawos-peligro:hover { background-color: #A5301F; }";
    gtk_css_provider_load_from_data(proveedor, css, -1, NULL);
    gtk_style_context_add_provider_for_screen(
        gdk_screen_get_default(), GTK_STYLE_PROVIDER(proveedor),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(proveedor);
}

/* ---------- Registro de un cliente nuevo ---------- */

/* Etiqueta de un campo del formulario, con un asterisco rojo si es
 * obligatorio (Telefono es el unico campo opcional del registro). */
static GtkWidget *crear_etiqueta_campo(const char *texto, gboolean obligatorio) {
    GtkWidget *lbl = gtk_label_new(NULL);
    gchar *markup = obligatorio
        ? g_strdup_printf("%s <span foreground='#C0392B'>*</span>", texto)
        : g_strdup(texto);
    gtk_label_set_markup(GTK_LABEL(lbl), markup);
    g_free(markup);
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    return lbl;
}

/* Mensaje bajo un campo (vacio = no se muestra): rojo para error,
 * verde para "esta bien". Se usa gtk_widget_set_no_show_all para que
 * gtk_widget_show_all() no lo vuelva a mostrar por error cuando esta
 * vacio. */
static void marcar_mensaje_campo(GtkWidget *lbl, const char *mensaje, gboolean es_valido) {
    if (!mensaje || mensaje[0] == '\0') {
        gtk_label_set_text(GTK_LABEL(lbl), "");
        gtk_widget_hide(lbl);
        return;
    }
    const char *color = es_valido ? "#1E8449" : "#C0392B";
    gchar *markup = g_strdup_printf("<span size='small' foreground='%s'>%s</span>", color, mensaje);
    gtk_label_set_markup(GTK_LABEL(lbl), markup);
    g_free(markup);
    gtk_widget_set_no_show_all(lbl, FALSE);
    gtk_widget_show(lbl);
}

/* Atajo para el caso de error (rojo), usado por los demas campos. */
static void marcar_error_campo(GtkWidget *lbl_error, const char *mensaje) {
    marcar_mensaje_campo(lbl_error, mensaje, FALSE);
}

static GtkWidget *crear_etiqueta_error(void) {
    GtkWidget *lbl = gtk_label_new("");
    gtk_widget_set_halign(lbl, GTK_ALIGN_START);
    gtk_widget_set_no_show_all(lbl, TRUE); /* oculta hasta que haga falta, show_all no la toca */
    return lbl;
}

/* Revisa en vivo (cada vez que se escribe una letra en Contrasena o
 * Confirmar contrasena) si coinciden, sin esperar a que se de clic en
 * "Registrarme" -- evita que el mensaje aparezca de golpe al final. */
typedef struct {
    GtkWidget *entry_pass;
    GtkWidget *entry_pass2;
    GtkWidget *error_pass;
    GtkWidget *error_pass2;
} ValidacionPassword;

static void on_password_changed(GtkEditable *editable, gpointer datos) {
    (void)editable;
    ValidacionPassword *v = datos;
    const char *pass = gtk_entry_get_text(GTK_ENTRY(v->entry_pass));
    const char *pass2 = gtk_entry_get_text(GTK_ENTRY(v->entry_pass2));
    if (pass[0] == '\0' || pass2[0] == '\0') {
        marcar_mensaje_campo(v->error_pass, NULL, FALSE);
        marcar_mensaje_campo(v->error_pass2, NULL, FALSE);
    } else if (strcmp(pass, pass2) != 0) {
        marcar_mensaje_campo(v->error_pass, "Las contrasenas no coinciden", FALSE);
        marcar_mensaje_campo(v->error_pass2, "Las contrasenas no coinciden", FALSE);
    } else {
        marcar_mensaje_campo(v->error_pass, "Las contrasenas coinciden", TRUE);
        marcar_mensaje_campo(v->error_pass2, "Las contrasenas coinciden", TRUE);
    }
}

static void mostrar_registro(GtkWindow *padre) {
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrarme como cliente", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Registrarme", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 380, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 4);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *entry_correo = gtk_entry_new();
    GtkWidget *entry_nombre = gtk_entry_new();
    GtkWidget *entry_telefono = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_telefono), "Opcional, numero de WhatsApp");
    GtkWidget *entry_pass = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass), FALSE);
    GtkWidget *entry_pass2 = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass2), FALSE);

    GtkWidget *error_correo = crear_etiqueta_error();
    GtkWidget *error_nombre = crear_etiqueta_error();
    GtkWidget *error_pass = crear_etiqueta_error();
    GtkWidget *error_pass2 = crear_etiqueta_error();

    ValidacionPassword vp = { entry_pass, entry_pass2, error_pass, error_pass2 };
    g_signal_connect(entry_pass, "changed", G_CALLBACK(on_password_changed), &vp);
    g_signal_connect(entry_pass2, "changed", G_CALLBACK(on_password_changed), &vp);

    int fila = 0;
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Correo:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_correo, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Nombre:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_nombre, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_nombre, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Telefono:", FALSE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_telefono, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Contrasena:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), crear_etiqueta_campo("Confirmar contrasena:", TRUE), 0, fila, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass2, 1, fila++, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), error_pass2, 1, fila++, 1, 1);

    GtkWidget *lbl_nota = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_nota), "<span size='small' foreground='#777777'>* Campo obligatorio</span>");
    gtk_widget_set_halign(lbl_nota, GTK_ALIGN_START);
    gtk_grid_attach(GTK_GRID(grid), lbl_nota, 0, fila++, 2, 1);

    gtk_widget_show_all(dialogo);
    for (;;) {
        if (gtk_dialog_run(GTK_DIALOG(dialogo)) != GTK_RESPONSE_OK) break;

        const char *correo = gtk_entry_get_text(GTK_ENTRY(entry_correo));
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(entry_nombre));
        const char *telefono = gtk_entry_get_text(GTK_ENTRY(entry_telefono));
        const char *pass = gtk_entry_get_text(GTK_ENTRY(entry_pass));
        const char *pass2 = gtk_entry_get_text(GTK_ENTRY(entry_pass2));

        marcar_error_campo(error_correo, NULL);
        marcar_error_campo(error_nombre, NULL);
        marcar_error_campo(error_pass, NULL);
        marcar_error_campo(error_pass2, NULL);

        gboolean ok = TRUE;
        if (correo[0] == '\0') { marcar_error_campo(error_correo, "Este campo es obligatorio"); ok = FALSE; }
        if (nombre[0] == '\0') { marcar_error_campo(error_nombre, "Este campo es obligatorio"); ok = FALSE; }
        if (pass[0] == '\0') { marcar_error_campo(error_pass, "Este campo es obligatorio"); ok = FALSE; }
        if (pass2[0] == '\0') { marcar_error_campo(error_pass2, "Este campo es obligatorio"); ok = FALSE; }
        if (pass[0] != '\0' && pass2[0] != '\0' && strcmp(pass, pass2) != 0) {
            marcar_error_campo(error_pass, "Las contrasenas no coinciden");
            marcar_error_campo(error_pass2, "Las contrasenas no coinciden");
            ok = FALSE;
        }
        if (!ok) continue;

        if (cliente_existe(correo)) {
            marcar_error_campo(error_correo, "Ya existe un cliente registrado con ese correo");
            continue;
        }
        if (cliente_registrar(correo, pass, nombre, telefono, ROL_CLIENTE_JEFE) != 0) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo completar el registro.", TRUE);
            continue;
        }
        mostrar_mensaje(GTK_WINDOW(dialogo), "Registro completado. Ya puedes iniciar sesion.", FALSE);
        break;
    }
    gtk_widget_destroy(dialogo);
}

/* ---------- Login ---------- */

static gboolean mostrar_login(Cliente *out) {
    for (;;) {
        GtkWidget *dialogo = gtk_dialog_new_with_buttons(
            "PawOS - Portal de Clientes", NULL, GTK_DIALOG_MODAL,
            "_Salir", GTK_RESPONSE_CANCEL,
            "_Registrarme", RESPUESTA_REGISTRARME,
            "_Iniciar sesion", GTK_RESPONSE_OK, NULL);
        gtk_window_set_default_size(GTK_WINDOW(dialogo), 360, -1);
        GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
        gtk_container_set_border_width(GTK_CONTAINER(area), 16);

        GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
        GtkWidget *lbl_titulo = gtk_label_new(NULL);
        gchar *markup = g_strdup_printf(
            "<span size='large' weight='bold'>\xF0\x9F\x90\xBE PawOS</span>\n<span size='small'>Portal de Clientes - v%s</span>",
            PAWOS_VERSION);
        gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup);
        g_free(markup);
        gtk_box_pack_start(GTK_BOX(caja), lbl_titulo, FALSE, FALSE, 4);

        GtkWidget *entry_correo = gtk_entry_new();
        gtk_entry_set_placeholder_text(GTK_ENTRY(entry_correo), "Correo");
        GtkWidget *entry_pass = gtk_entry_new();
        gtk_entry_set_visibility(GTK_ENTRY(entry_pass), FALSE);
        gtk_entry_set_placeholder_text(GTK_ENTRY(entry_pass), "Contrasena");
        gtk_entry_set_activates_default(GTK_ENTRY(entry_pass), TRUE);

        gtk_box_pack_start(GTK_BOX(caja), entry_correo, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(caja), entry_pass, FALSE, FALSE, 0);
        gtk_container_add(GTK_CONTAINER(area), caja);

        gtk_dialog_set_default_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
        gtk_widget_show_all(dialogo);

        int resp = gtk_dialog_run(GTK_DIALOG(dialogo));

        if (resp == GTK_RESPONSE_OK) {
            const char *correo = gtk_entry_get_text(GTK_ENTRY(entry_correo));
            const char *pass = gtk_entry_get_text(GTK_ENTRY(entry_pass));
            Cliente candidato;
            if (correo[0] != '\0' && cliente_autenticar(correo, pass, &candidato) == 0) {
                *out = candidato;
                gtk_widget_destroy(dialogo);
                return TRUE;
            }
            gtk_widget_destroy(dialogo);
            mostrar_mensaje(NULL, "Correo o contrasena incorrectos.", TRUE);
            continue;
        } else if (resp == RESPUESTA_REGISTRARME) {
            gtk_widget_destroy(dialogo);
            mostrar_registro(NULL);
            continue;
        } else {
            gtk_widget_destroy(dialogo);
            return FALSE;
        }
    }
}

/* ---------- Mis recordatorios de vacunas ---------- */

static void calcular_estado(const char *fecha_proxima, const char *hoy,
                             const char **estado_out, const char **color_out) {
    if (!fecha_proxima || fecha_proxima[0] == '\0') {
        *estado_out = "-";
        *color_out = "#555555";
        return;
    }
    int cmp = strcmp(fecha_proxima, hoy);
    if (cmp < 0) { *estado_out = "VENCIDA"; *color_out = "#C0392B"; }
    else if (cmp == 0) { *estado_out = "HOY"; *color_out = "#D68910"; }
    else { *estado_out = "Al dia"; *color_out = "#1E8449"; }
}

static void cargar_mis_vacunas(ContextoApp *ctx) {
    gtk_list_store_clear(ctx->store_vacunas);

    char hoy[16];
    time_t t = time(NULL);
    struct tm tmv;
    localtime_r(&t, &tmv);
    strftime(hoy, sizeof(hoy), "%Y-%m-%d", &tmv);

    Vacuna *vs;
    int n;
    if (vacuna_listar(&vs, &n) != 0) return;

    for (int i = 0; i < n; i++) {
        if (vs[i].cliente_id != ctx->cliente.id) continue;

        Mascota m;
        const char *nombre_mascota = "(mascota desconocida)";
        if (mascota_buscar_por_id(vs[i].mascota_id, &m) == 0) nombre_mascota = m.nombre;

        const char *estado, *color;
        calcular_estado(vs[i].fecha_proxima, hoy, &estado, &color);

        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_vacunas, &iter);
        gtk_list_store_set(ctx->store_vacunas, &iter,
            COL_V_MASCOTA, nombre_mascota,
            COL_V_VACUNA, vs[i].nombre_vacuna,
            COL_V_PROXIMA, vs[i].fecha_proxima,
            COL_V_ESTADO, estado,
            COL_V_COLOR, color,
            -1);
    }
    free(vs);
}

static void on_actualizar_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    cargar_mis_vacunas((ContextoApp *)datos);
}

/* ---------- Foto de perfil ---------- */

static void poner_avatar_placeholder(ContextoApp *ctx) {
    gtk_image_set_from_icon_name(GTK_IMAGE(ctx->imagen_avatar), "avatar-default-symbolic", GTK_ICON_SIZE_DIALOG);
}

/* Trae la foto guardada (texto base64) desde db.c, la decodifica y la
 * muestra en ctx->imagen_avatar. Si el cliente no tiene foto, o algo
 * sale mal al decodificarla, muestra un icono generico en su lugar. */
static void cargar_avatar(ContextoApp *ctx) {
    char *foto_b64 = NULL;
    if (cliente_obtener_foto(ctx->cliente.id, &foto_b64) != 0 || !foto_b64 || foto_b64[0] == '\0') {
        free(foto_b64);
        poner_avatar_placeholder(ctx);
        return;
    }

    gsize len_bin = 0;
    guchar *datos_bin = g_base64_decode(foto_b64, &len_bin);
    free(foto_b64);
    if (!datos_bin || len_bin == 0) {
        g_free(datos_bin);
        poner_avatar_placeholder(ctx);
        return;
    }

    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    gboolean ok = gdk_pixbuf_loader_write(loader, datos_bin, len_bin, NULL);
    ok = ok && gdk_pixbuf_loader_close(loader, NULL);
    GdkPixbuf *pix = ok ? gdk_pixbuf_loader_get_pixbuf(loader) : NULL;
    if (pix) {
        GdkPixbuf *escalado = gdk_pixbuf_scale_simple(pix, FOTO_AVATAR_SIZE, FOTO_AVATAR_SIZE, GDK_INTERP_BILINEAR);
        gtk_image_set_from_pixbuf(GTK_IMAGE(ctx->imagen_avatar), escalado);
        g_object_unref(escalado);
    } else {
        poner_avatar_placeholder(ctx);
    }
    g_object_unref(loader);
    g_free(datos_bin);
}

/* Estado del dialogo de recorte: deja al usuario arrastrar el mouse
 * sobre la imagen para elegir libremente que region quiere usar como
 * foto de perfil, y despues MOVER el recuadro o agrandarlo/achicarlo
 * desde sus 4 esquinas (como en el recorte de foto de perfil de
 * cualquier red social), en vez de tener que volver a dibujarlo. */
typedef enum {
    MODO_NINGUNO = 0,
    MODO_DIBUJANDO,
    MODO_MOVIENDO,
    MODO_REDIM_TL,
    MODO_REDIM_TR,
    MODO_REDIM_BL,
    MODO_REDIM_BR
} ModoRecorte;

typedef struct {
    GdkPixbuf  *pixbuf;
    int         ancho_img, alto_img;
    gboolean    hay_seleccion;
    double      x, y, w, h;        /* seleccion actual (normalizada) */
    ModoRecorte modo;
    double      ancla_x, ancla_y;  /* MODO_DIBUJANDO: punto donde empezo el arrastre */
    double      offset_x, offset_y; /* MODO_MOVIENDO: desfase click -> esquina sup-izq */
    GtkWidget  *btn_ok;
} ContextoRecorte;

#define RECORTE_TAM_ASA 10.0 /* radio (en pixeles) para "agarrar" una esquina */

static ModoRecorte recorte_detectar_modo(ContextoRecorte *r, double px, double py) {
    if (!r->hay_seleccion) return MODO_DIBUJANDO;
    double x0 = r->x, y0 = r->y, x1 = r->x + r->w, y1 = r->y + r->h;
    const double m = RECORTE_TAM_ASA;
    if (fabs(px - x0) <= m && fabs(py - y0) <= m) return MODO_REDIM_TL;
    if (fabs(px - x1) <= m && fabs(py - y0) <= m) return MODO_REDIM_TR;
    if (fabs(px - x0) <= m && fabs(py - y1) <= m) return MODO_REDIM_BL;
    if (fabs(px - x1) <= m && fabs(py - y1) <= m) return MODO_REDIM_BR;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) return MODO_MOVIENDO;
    return MODO_DIBUJANDO;
}

static gboolean recorte_on_draw(GtkWidget *widget, cairo_t *cr, gpointer datos) {
    (void)widget;
    ContextoRecorte *r = datos;
    int w = gdk_pixbuf_get_width(r->pixbuf);
    int h = gdk_pixbuf_get_height(r->pixbuf);
    gdk_cairo_set_source_pixbuf(cr, r->pixbuf, 0, 0);
    cairo_paint(cr);

    if (r->hay_seleccion || r->modo == MODO_DIBUJANDO) {
        double x = r->x, y = r->y, sw = r->w, sh = r->h;

        cairo_set_fill_rule(cr, CAIRO_FILL_RULE_EVEN_ODD);
        cairo_set_source_rgba(cr, 0, 0, 0, 0.45);
        cairo_rectangle(cr, 0, 0, w, h);
        cairo_rectangle(cr, x, y, sw, sh);
        cairo_fill(cr);

        cairo_set_source_rgb(cr, 1, 1, 1);
        cairo_set_line_width(cr, 2.0);
        cairo_rectangle(cr, x, y, sw, sh);
        cairo_stroke(cr);

        /* Asas en las 4 esquinas: avisan que se puede agrandar/achicar */
        double esquinas[4][2] = { {x, y}, {x + sw, y}, {x, y + sh}, {x + sw, y + sh} };
        for (int i = 0; i < 4; i++) {
            cairo_rectangle(cr, esquinas[i][0] - 4, esquinas[i][1] - 4, 8, 8);
            cairo_set_source_rgb(cr, 1, 1, 1);
            cairo_fill_preserve(cr);
            cairo_set_source_rgb(cr, 0.137, 0.573, 0.294); /* verde PawOS */
            cairo_set_line_width(cr, 1.5);
            cairo_stroke(cr);
        }
    }
    return FALSE;
}

static gboolean recorte_on_press(GtkWidget *widget, GdkEventButton *evento, gpointer datos) {
    ContextoRecorte *r = datos;
    r->modo = recorte_detectar_modo(r, evento->x, evento->y);
    if (r->modo == MODO_DIBUJANDO) {
        r->ancla_x = evento->x;
        r->ancla_y = evento->y;
        r->x = evento->x; r->y = evento->y; r->w = 0; r->h = 0;
        r->hay_seleccion = FALSE;
        gtk_widget_set_sensitive(r->btn_ok, FALSE);
    } else if (r->modo == MODO_MOVIENDO) {
        r->offset_x = evento->x - r->x;
        r->offset_y = evento->y - r->y;
    }
    gtk_widget_queue_draw(widget);
    return TRUE;
}

static gboolean recorte_on_motion(GtkWidget *widget, GdkEventMotion *evento, gpointer datos) {
    ContextoRecorte *r = datos;
    if (r->modo == MODO_NINGUNO) return FALSE;

    double px = evento->x, py = evento->y;
    if (px < 0) px = 0; if (px > r->ancho_img) px = r->ancho_img;
    if (py < 0) py = 0; if (py > r->alto_img) py = r->alto_img;

    switch (r->modo) {
        case MODO_DIBUJANDO:
            r->x = MIN(r->ancla_x, px);
            r->y = MIN(r->ancla_y, py);
            r->w = fabs(px - r->ancla_x);
            r->h = fabs(py - r->ancla_y);
            break;
        case MODO_MOVIENDO: {
            double nx = px - r->offset_x, ny = py - r->offset_y;
            if (nx < 0) nx = 0;
            if (ny < 0) ny = 0;
            if (nx + r->w > r->ancho_img) nx = r->ancho_img - r->w;
            if (ny + r->h > r->alto_img) ny = r->alto_img - r->h;
            r->x = nx; r->y = ny;
            break;
        }
        case MODO_REDIM_TL: {
            double x1 = r->x + r->w, y1 = r->y + r->h;
            double nx = MIN(px, x1 - RECORTE_TAM_ASA), ny = MIN(py, y1 - RECORTE_TAM_ASA);
            r->x = nx; r->y = ny; r->w = x1 - nx; r->h = y1 - ny;
            break;
        }
        case MODO_REDIM_TR: {
            double x0 = r->x, y1 = r->y + r->h;
            double nx1 = MAX(px, x0 + RECORTE_TAM_ASA), ny = MIN(py, y1 - RECORTE_TAM_ASA);
            r->y = ny; r->w = nx1 - x0; r->h = y1 - ny;
            break;
        }
        case MODO_REDIM_BL: {
            double x1 = r->x + r->w, y0 = r->y;
            double nx = MIN(px, x1 - RECORTE_TAM_ASA), ny1 = MAX(py, y0 + RECORTE_TAM_ASA);
            r->x = nx; r->w = x1 - nx; r->h = ny1 - y0;
            break;
        }
        case MODO_REDIM_BR: {
            double x0 = r->x, y0 = r->y;
            double nx1 = MAX(px, x0 + RECORTE_TAM_ASA), ny1 = MAX(py, y0 + RECORTE_TAM_ASA);
            r->w = nx1 - x0; r->h = ny1 - y0;
            break;
        }
        default:
            return FALSE;
    }
    gtk_widget_queue_draw(widget);
    return TRUE;
}

static gboolean recorte_on_release(GtkWidget *widget, GdkEventButton *evento, gpointer datos) {
    (void)evento;
    ContextoRecorte *r = datos;
    r->modo = MODO_NINGUNO;
    r->hay_seleccion = (r->w >= 15 && r->h >= 15);
    gtk_widget_set_sensitive(r->btn_ok, r->hay_seleccion);
    gtk_widget_queue_draw(widget);
    return TRUE;
}

/* Muestra la imagen cargada y deja que el usuario dibuje un recuadro
 * de tamano libre, y luego lo MUEVA (arrastrando por dentro) o lo
 * AGRANDE/ACHIQUE (arrastrando cualquiera de sus 4 esquinas) tantas
 * veces como quiera antes de confirmar. Devuelve un GdkPixbuf nuevo
 * (liberar con g_object_unref) con solo esa region, o NULL si
 * cancelo o no llego a dejar una seleccion valida. */
static GdkPixbuf *mostrar_dialogo_recorte(GtkWindow *padre, GdkPixbuf *imagen_original) {
    int ow = gdk_pixbuf_get_width(imagen_original);
    int oh = gdk_pixbuf_get_height(imagen_original);
    double escala = 1.0;
    if (ow > RECORTE_MAX_DIM || oh > RECORTE_MAX_DIM) {
        escala = (double)RECORTE_MAX_DIM / (double)(ow > oh ? ow : oh);
    }
    int dw = (int)(ow * escala), dh = (int)(oh * escala);
    GdkPixbuf *mostrado = (escala < 1.0)
        ? gdk_pixbuf_scale_simple(imagen_original, dw, dh, GDK_INTERP_BILINEAR)
        : GDK_PIXBUF(g_object_ref(imagen_original));

    ContextoRecorte r;
    memset(&r, 0, sizeof(r));
    r.pixbuf = mostrado;
    r.ancho_img = dw;
    r.alto_img = dh;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons("Recortar foto de perfil", padre, GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Usar esta seleccion", GTK_RESPONSE_OK, NULL);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 10);

    GtkWidget *lbl_ayuda = gtk_label_new(
        "Dibuja un recuadro arrastrando el mouse. Luego puedes moverlo (arrastra por dentro) o "
        "agrandarlo/achicarlo (arrastra cualquier esquina).");
    gtk_label_set_line_wrap(GTK_LABEL(lbl_ayuda), TRUE);
    gtk_box_pack_start(GTK_BOX(area), lbl_ayuda, FALSE, FALSE, 4);

    GtkWidget *drawing = gtk_drawing_area_new();
    gtk_widget_set_size_request(drawing, dw, dh);
    gtk_widget_add_events(drawing, GDK_BUTTON_PRESS_MASK | GDK_BUTTON_RELEASE_MASK | GDK_POINTER_MOTION_MASK);
    gtk_box_pack_start(GTK_BOX(area), drawing, TRUE, TRUE, 4);

    r.btn_ok = gtk_dialog_get_widget_for_response(GTK_DIALOG(dialogo), GTK_RESPONSE_OK);
    gtk_widget_set_sensitive(r.btn_ok, FALSE);

    g_signal_connect(drawing, "draw", G_CALLBACK(recorte_on_draw), &r);
    g_signal_connect(drawing, "button-press-event", G_CALLBACK(recorte_on_press), &r);
    g_signal_connect(drawing, "motion-notify-event", G_CALLBACK(recorte_on_motion), &r);
    g_signal_connect(drawing, "button-release-event", G_CALLBACK(recorte_on_release), &r);

    gtk_widget_show_all(dialogo);
    int resp = gtk_dialog_run(GTK_DIALOG(dialogo));

    GdkPixbuf *resultado = NULL;
    if (resp == GTK_RESPONSE_OK && r.hay_seleccion) {
        int x = (int)r.x, y = (int)r.y;
        int sw = (int)r.w, sh = (int)r.h;
        if (x < 0) x = 0;
        if (y < 0) y = 0;
        if (x + sw > dw) sw = dw - x;
        if (y + sh > dh) sh = dh - y;
        if (sw > 0 && sh > 0) {
            GdkPixbuf *sub = gdk_pixbuf_new_subpixbuf(mostrado, x, y, sw, sh);
            resultado = gdk_pixbuf_copy(sub);
            g_object_unref(sub);
        }
    }

    gtk_widget_destroy(dialogo);
    g_object_unref(mostrado);
    return resultado;
}

static void on_cambiar_foto_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    GtkWidget *selector = gtk_file_chooser_dialog_new("Elegir foto de perfil", GTK_WINDOW(ctx->ventana),
        GTK_FILE_CHOOSER_ACTION_OPEN, "_Cancelar", GTK_RESPONSE_CANCEL, "_Abrir", GTK_RESPONSE_ACCEPT, NULL);

    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Imagenes (PNG, JPG)");
    gtk_file_filter_add_mime_type(filtro, "image/png");
    gtk_file_filter_add_mime_type(filtro, "image/jpeg");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(selector), filtro);

    if (gtk_dialog_run(GTK_DIALOG(selector)) != GTK_RESPONSE_ACCEPT) {
        gtk_widget_destroy(selector);
        return;
    }
    char *ruta = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(selector));
    gtk_widget_destroy(selector);
    if (!ruta) return;

    GError *error = NULL;
    GdkPixbuf *original = gdk_pixbuf_new_from_file(ruta, &error);
    g_free(ruta);
    if (!original) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo abrir esa imagen.", TRUE);
        if (error) g_error_free(error);
        return;
    }

    GdkPixbuf *recortada = mostrar_dialogo_recorte(GTK_WINDOW(ctx->ventana), original);
    g_object_unref(original);
    if (!recortada) return; /* cancelo el recorte, o no selecciono nada */

    /* Limita el maximo en pixeles para no inflar la BD remota con
     * fotos enormes -- el usuario ya eligio la forma/tamano relativo
     * que quiere en el recorte, esto solo evita archivos gigantes. */
    int rw = gdk_pixbuf_get_width(recortada), rh = gdk_pixbuf_get_height(recortada);
    if (rw > 512 || rh > 512) {
        double esc = 512.0 / (double)(rw > rh ? rw : rh);
        GdkPixbuf *mas_chica = gdk_pixbuf_scale_simple(recortada, (int)(rw * esc), (int)(rh * esc), GDK_INTERP_BILINEAR);
        g_object_unref(recortada);
        recortada = mas_chica;
    }

    gchar *buffer = NULL;
    gsize tam_buffer = 0;
    if (!gdk_pixbuf_save_to_buffer(recortada, &buffer, &tam_buffer, "png", &error, NULL)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo procesar la imagen recortada.", TRUE);
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
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo guardar la foto en el servidor.", TRUE);
        return;
    }
    cargar_avatar(ctx);
    mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Foto de perfil actualizada.", FALSE);
}

/* ---------- Editar mi perfil ---------- */

static void on_editar_perfil_clicked(GtkButton *btn, gpointer datos) {
    (void)btn;
    ContextoApp *ctx = datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Editar mi perfil", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
        "_Cancelar", GTK_RESPONSE_CANCEL, "_Guardar", GTK_RESPONSE_OK, NULL);
    gtk_window_set_default_size(GTK_WINDOW(dialogo), 360, -1);
    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    gtk_container_set_border_width(GTK_CONTAINER(area), 14);
    GtkWidget *grid = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 10);
    gtk_container_add(GTK_CONTAINER(area), grid);

    GtkWidget *entry_nombre = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(entry_nombre), ctx->cliente.nombre);
    GtkWidget *entry_pass_nueva = gtk_entry_new();
    gtk_entry_set_visibility(GTK_ENTRY(entry_pass_nueva), FALSE);
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry_pass_nueva), "Dejar vacia para no cambiarla");

    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nombre:"), 0, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_nombre, 1, 0, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), gtk_label_new("Nueva contrasena:"), 0, 1, 1, 1);
    gtk_grid_attach(GTK_GRID(grid), entry_pass_nueva, 1, 1, 1, 1);

    gtk_widget_show_all(dialogo);
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        const char *nombre = gtk_entry_get_text(GTK_ENTRY(entry_nombre));
        const char *pass_nueva = gtk_entry_get_text(GTK_ENTRY(entry_pass_nueva));
        if (nombre[0] == '\0') {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "El nombre no puede quedar vacio.", TRUE);
        } else if (cliente_actualizar(ctx->cliente.id, nombre, pass_nueva) != 0) {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo actualizar el perfil.", TRUE);
        } else {
            snprintf(ctx->cliente.nombre, sizeof(ctx->cliente.nombre), "%s", nombre);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Perfil actualizado.", FALSE);
        }
    }
    gtk_widget_destroy(dialogo);
}

/* ---------- Ventana principal ---------- */

static void construir_ventana(ContextoApp *ctx) {
    ctx->ventana = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(ctx->ventana), "PawOS - Portal de Clientes");
    gtk_window_set_default_size(GTK_WINDOW(ctx->ventana), 820, 560);
    gtk_window_set_position(GTK_WINDOW(ctx->ventana), GTK_WIN_POS_CENTER);
    g_signal_connect(ctx->ventana, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *caja_raiz = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_container_add(GTK_CONTAINER(ctx->ventana), caja_raiz);

    GtkWidget *encabezado = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(encabezado), "pawos-header");
    GtkWidget *lbl_titulo = gtk_label_new(NULL);
    gchar *markup_titulo = g_strdup_printf(
        "<span size='large' weight='bold'>\xF0\x9F\x90\xBE Hola, %s</span>  <span size='small'>(%s)</span>",
        ctx->cliente.nombre, cliente_rol_nombre(ctx->cliente.rol));
    gtk_label_set_markup(GTK_LABEL(lbl_titulo), markup_titulo);
    g_free(markup_titulo);
    gtk_box_pack_start(GTK_BOX(encabezado), lbl_titulo, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_raiz), encabezado, FALSE, FALSE, 0);

    GtkWidget *contenido = gtk_box_new(GTK_ORIENTATION_VERTICAL, 14);
    gtk_container_set_border_width(GTK_CONTAINER(contenido), 16);
    gtk_widget_set_vexpand(contenido, TRUE);
    gtk_box_pack_start(GTK_BOX(caja_raiz), contenido, TRUE, TRUE, 0);

    /* Tarjeta de datos de contacto (foto + correo/telefono + acciones) */
    GtkWidget *tarjeta_perfil = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_perfil), "pawos-tarjeta");

    GtkWidget *caja_avatar = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
    ctx->imagen_avatar = gtk_image_new();
    gtk_widget_set_size_request(ctx->imagen_avatar, FOTO_AVATAR_SIZE, FOTO_AVATAR_SIZE);
    gtk_box_pack_start(GTK_BOX(caja_avatar), ctx->imagen_avatar, FALSE, FALSE, 0);
    GtkWidget *btn_cambiar_foto = gtk_button_new_with_label("Cambiar foto");
    g_signal_connect(btn_cambiar_foto, "clicked", G_CALLBACK(on_cambiar_foto_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(caja_avatar), btn_cambiar_foto, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), caja_avatar, FALSE, FALSE, 0);

    GtkWidget *caja_datos = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_widget_set_hexpand(caja_datos, TRUE);
    gtk_widget_set_valign(caja_datos, GTK_ALIGN_CENTER);
    gchar *texto_datos = g_strdup_printf("Correo: %s\nTelefono: %s",
        ctx->cliente.correo, ctx->cliente.telefono[0] ? ctx->cliente.telefono : "(no registrado)");
    GtkWidget *lbl_datos = gtk_label_new(texto_datos);
    g_free(texto_datos);
    gtk_widget_set_halign(lbl_datos, GTK_ALIGN_START);
    gtk_box_pack_start(GTK_BOX(caja_datos), lbl_datos, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), caja_datos, TRUE, TRUE, 0);

    GtkWidget *btn_editar_perfil = gtk_button_new_with_label("Editar mi perfil");
    g_signal_connect(btn_editar_perfil, "clicked", G_CALLBACK(on_editar_perfil_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), btn_editar_perfil, FALSE, FALSE, 0);

    GtkWidget *btn_cerrar_sesion = gtk_button_new_with_label("Cerrar sesion");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_cerrar_sesion), "pawos-peligro");
    g_signal_connect_swapped(btn_cerrar_sesion, "clicked", G_CALLBACK(gtk_widget_destroy), ctx->ventana);
    gtk_box_pack_start(GTK_BOX(tarjeta_perfil), btn_cerrar_sesion, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(contenido), tarjeta_perfil, FALSE, FALSE, 0);

    /* Seccion de recordatorios de vacunas */
    GtkWidget *barra_vacunas = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *lbl_seccion = gtk_label_new(NULL);
    gtk_label_set_markup(GTK_LABEL(lbl_seccion), "<span weight='bold' size='medium'>Mis recordatorios de vacunas</span>");
    gtk_widget_set_halign(lbl_seccion, GTK_ALIGN_START);
    gtk_widget_set_hexpand(lbl_seccion, TRUE);
    gtk_box_pack_start(GTK_BOX(barra_vacunas), lbl_seccion, TRUE, TRUE, 0);

    GtkWidget *btn_actualizar = gtk_button_new_with_label("Actualizar");
    gtk_style_context_add_class(gtk_widget_get_style_context(btn_actualizar), "pawos-accion");
    g_signal_connect(btn_actualizar, "clicked", G_CALLBACK(on_actualizar_clicked), ctx);
    gtk_box_pack_start(GTK_BOX(barra_vacunas), btn_actualizar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), barra_vacunas, FALSE, FALSE, 0);

    GtkWidget *tarjeta_vacunas = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_style_context_add_class(gtk_widget_get_style_context(tarjeta_vacunas), "pawos-tarjeta");
    gtk_widget_set_vexpand(tarjeta_vacunas, TRUE);

    GtkWidget *scroll = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroll), GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_vexpand(scroll, TRUE);

    ctx->store_vacunas = gtk_list_store_new(N_COLUMNAS_VACUNA,
        G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *treeview = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_vacunas));

    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Mascota", gtk_cell_renderer_text_new(), "text", COL_V_MASCOTA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Vacuna", gtk_cell_renderer_text_new(), "text", COL_V_VACUNA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Proxima dosis", gtk_cell_renderer_text_new(), "text", COL_V_PROXIMA, NULL);
    gtk_tree_view_insert_column_with_attributes(GTK_TREE_VIEW(treeview),
        -1, "Estado", gtk_cell_renderer_text_new(), "text", COL_V_ESTADO, "foreground", COL_V_COLOR, NULL);

    gtk_container_add(GTK_CONTAINER(scroll), treeview);
    gtk_box_pack_start(GTK_BOX(tarjeta_vacunas), scroll, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(contenido), tarjeta_vacunas, TRUE, TRUE, 0);

    gtk_widget_show_all(ctx->ventana);
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);

    const char *ruta_bd = (argc > 1) ? argv[1] : RUTA_BD_DEFECTO;
    if (db_init(ruta_bd) != 0) {
        fprintf(stderr, "Aviso: no se pudo usar %s, usando ./pawos.db\n", ruta_bd);
        if (db_init("pawos.db") != 0) {
            fprintf(stderr, "No se pudo inicializar la base de datos.\n");
            return 1;
        }
    }

    aplicar_estilos_simples();

    ContextoApp ctx;
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
    return 0;
}
