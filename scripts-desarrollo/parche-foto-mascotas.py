#!/usr/bin/env python3
"""
parche-foto-mascotas.py  (ETAPA 1: base de datos + PawOS Refugio GUI)

Agrega fotos a las mascotas SIN quitar nada de lo existente:
  - src/db/db.h / db.c : mascota_guardar_foto, mascota_obtener_foto,
                         mascota_ultimo_id (no se toca la estructura Mascota
                         ni ninguna funcion anterior).
  - src/main_gtk.c     : "Elegir foto (opcional)" al registrar una mascota,
                         y boton "Foto" para ver/cambiar la foto de una
                         mascota ya registrada (el voluntario solo la ve).
                         La imagen se reduce a 300 px y se guarda en JPEG
                         base64 (igual que la foto de perfil de clientes).

ANTES de compilar, en SQL Server (SSMS) debe existir la columna:
    ALTER TABLE mascotas ADD foto_base64 VARCHAR(MAX) NULL;

Uso (parado en la raiz del repo):
    python3 parche-foto-mascotas.py
    make
"""

import shutil
import sys

DB_H = "src/db/db.h"
DB_C = "src/db/db.c"
GTK_C = "src/main_gtk.c"

# ------------------------------------------------------------------ db.h
ANCLA_H = r"""int  mascota_buscar_por_id(int id, Mascota *out);"""
NUEVO_H = r"""int  mascota_buscar_por_id(int id, Mascota *out);
/* Foto de la mascota: JPEG en base64 (columna foto_base64, SQL Server). */
int  mascota_guardar_foto(int id, const char *foto_base64);
int  mascota_obtener_foto(int id, char **out_foto_base64); /* liberar con free(); "" si no tiene */
int  mascota_ultimo_id(const char *nombre, const char *fecha_ingreso, int *id_out);"""

# ------------------------------------------------------------------ db.c
ANCLA_C = r"""/* ---------------- Vacunas ---------------- */

int vacuna_agregar(const Vacuna *v) {"""
NUEVO_C = r"""/* ---------- Foto de la Mascota ----------
 * Texto base64 (JPEG reducido) en mascotas.foto_base64, igual que la
 * foto de perfil de clientes. Se pide por separado (no viaja en las
 * listas) para que listar mascotas siga siendo rapido. */
int mascota_guardar_foto(int id, const char *foto_base64) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "UPDATE mascotas SET foto_base64=? WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    const char *foto = foto_base64 ? foto_base64 : "";
    SQLLEN len_foto = SQL_NTS;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_LONGVARCHAR, (SQLULEN)strlen(foto), 0, (SQLPOINTER)foto, 0, &len_foto);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int ok = SQL_SUCCEEDED(SQLExecute(hstmt)) ? 0 : -1;
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

int mascota_obtener_foto(int id, char **out_foto_base64) {
    *out_foto_base64 = NULL;
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    const char *sql = "SELECT foto_base64 FROM mascotas WHERE id=?;";
    SQLPrepare(hstmt, (SQLCHAR *)sql, SQL_NTS);
    SQLINTEGER id_val = id;
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_LONG, SQL_INTEGER, 0, 0, &id_val, 0, NULL);
    int ok = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        size_t cap = 8192, usado = 0;
        char *buf = malloc(cap);
        buf[0] = '\0';
        SQLRETURN ret;
        char trozo[4096];
        SQLLEN ind;
        do {
            ret = SQLGetData(hstmt, 1, SQL_C_CHAR, trozo, sizeof(trozo), &ind);
            if (ind == SQL_NULL_DATA || !SQL_SUCCEEDED(ret)) break;
            size_t len_trozo = strlen(trozo);
            if (usado + len_trozo + 1 > cap) {
                cap = (usado + len_trozo + 1) * 2;
                buf = realloc(buf, cap);
            }
            memcpy(buf + usado, trozo, len_trozo);
            usado += len_trozo;
            buf[usado] = '\0';
        } while (ret == SQL_SUCCESS_WITH_INFO);
        *out_foto_base64 = buf;
        ok = 0;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

/* Id de la mascota mas reciente con ese nombre y fecha de ingreso
 * (para guardar la foto justo despues de registrarla). */
int mascota_ultimo_id(const char *nombre, const char *fecha_ingreso, int *id_out) {
    SQLHENV henv; SQLHDBC hdbc;
    if (api_conectar(&henv, &hdbc) != 0) return -1;
    SQLHSTMT hstmt;
    if (SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt) != SQL_SUCCESS) {
        api_desconectar(henv, hdbc);
        return -1;
    }
    SQLPrepare(hstmt, (SQLCHAR *)
        "SELECT TOP 1 id FROM mascotas WHERE nombre=? AND fecha_ingreso=? ORDER BY id DESC;", SQL_NTS);
    char nombre_buf[64], fecha_buf[16];
    snprintf(nombre_buf, sizeof(nombre_buf), "%s", nombre);
    snprintf(fecha_buf, sizeof(fecha_buf), "%s", fecha_ingreso);
    SQLBindParameter(hstmt, 1, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(nombre_buf) - 1, 0, nombre_buf, 0, NULL);
    SQLBindParameter(hstmt, 2, SQL_PARAM_INPUT, SQL_C_CHAR, SQL_VARCHAR, sizeof(fecha_buf) - 1, 0, fecha_buf, 0, NULL);
    int ok = -1;
    if (SQL_SUCCEEDED(SQLExecute(hstmt)) && SQLFetch(hstmt) == SQL_SUCCESS) {
        SQLINTEGER v = 0;
        SQLLEN ind;
        SQLGetData(hstmt, 1, SQL_C_SLONG, &v, 0, &ind);
        *id_out = (int)v;
        ok = 0;
    }
    SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
    api_desconectar(henv, hdbc);
    return ok;
}

/* ---------------- Vacunas ---------------- */

int vacuna_agregar(const Vacuna *v) {"""

# --------------------------------------------------------------- main_gtk.c
# A: ayudantes de foto + handler del dialogo Registrar (antes de on_registrar_clicked)
ANCLA_A = r"""static void on_registrar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrar nueva mascota", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,"""
NUEVO_A = r"""/* ---------- Fotos de mascotas (ayudantes) ---------- */

static GdkPixbuf *foto_pixbuf_desde_base64(const char *b64) {
    if (!b64 || !b64[0]) return NULL;
    gsize largo = 0;
    guchar *datos = g_base64_decode(b64, &largo);
    if (!datos || largo == 0) { g_free(datos); return NULL; }
    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    GdkPixbuf *res = NULL;
    if (gdk_pixbuf_loader_write(loader, datos, largo, NULL)) {
        gdk_pixbuf_loader_close(loader, NULL);
        GdkPixbuf *pb = gdk_pixbuf_loader_get_pixbuf(loader);
        if (pb) res = g_object_ref(pb);
    } else {
        gdk_pixbuf_loader_close(loader, NULL);
    }
    g_object_unref(loader);
    g_free(datos);
    return res;
}

/* Devuelve una copia reducida (sin agrandar) que cabe en max_lado. */
static GdkPixbuf *foto_escalar(GdkPixbuf *src, int max_lado) {
    int w = gdk_pixbuf_get_width(src), h = gdk_pixbuf_get_height(src);
    if (w <= max_lado && h <= max_lado) return g_object_ref(src);
    double f = (double)max_lado / (double)(w > h ? w : h);
    int nw = (int)(w * f), nh = (int)(h * f);
    if (nw < 1) nw = 1;
    if (nh < 1) nh = 1;
    return gdk_pixbuf_scale_simple(src, nw, nh, GDK_INTERP_BILINEAR);
}

/* Lee la imagen, la endereza (EXIF), la reduce a max_lado y la devuelve
 * como JPEG en base64 (liberar con g_free). NULL si no se pudo leer. */
static gchar *foto_archivo_a_base64(const char *ruta, int max_lado, GdkPixbuf **vista_out) {
    if (vista_out) *vista_out = NULL;
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
    GdkPixbuf *peq = foto_escalar(base, max_lado);
    g_object_unref(base);
    gchar *b64 = NULL;
    gchar *buf = NULL;
    gsize largo = 0;
    if (peq && gdk_pixbuf_save_to_buffer(peq, &buf, &largo, "jpeg", NULL, "quality", "85", NULL)) {
        b64 = g_base64_encode((const guchar *)buf, largo);
        g_free(buf);
    }
    if (peq) {
        if (vista_out && b64) *vista_out = g_object_ref(peq);
        g_object_unref(peq);
    }
    return b64;
}

/* Selector de imagen (PNG/JPEG). Devuelve la ruta (g_free) o NULL. */
static char *elegir_imagen_ruta(GtkWindow *padre) {
    GtkWidget *dialogo = gtk_file_chooser_dialog_new(
        "Elegir foto", padre, GTK_FILE_CHOOSER_ACTION_OPEN,
        "Cancelar", GTK_RESPONSE_CANCEL,
        "Elegir", GTK_RESPONSE_ACCEPT,
        NULL);
    GtkFileFilter *filtro = gtk_file_filter_new();
    gtk_file_filter_set_name(filtro, "Imagenes");
    gtk_file_filter_add_mime_type(filtro, "image/png");
    gtk_file_filter_add_mime_type(filtro, "image/jpeg");
    gtk_file_chooser_add_filter(GTK_FILE_CHOOSER(dialogo), filtro);
    char *ruta = NULL;
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_ACCEPT)
        ruta = gtk_file_chooser_get_filename(GTK_FILE_CHOOSER(dialogo));
    gtk_widget_destroy(dialogo);
    return ruta;
}

/* referencias[0] = GtkImage de vista previa, referencias[1] = dialogo padre.
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
    }
    g_object_set_data_full(G_OBJECT(refs[0]), "foto_base64", b64, g_free);
    if (vista) {
        GdkPixbuf *mini = foto_escalar(vista, 96);
        gtk_image_set_from_pixbuf(GTK_IMAGE(refs[0]), mini);
        g_object_unref(mini);
        g_object_unref(vista);
    }
}

static void on_registrar_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        "Registrar nueva mascota", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,"""

# B: fila "Foto" en el formulario de registro
ANCLA_B = r"""    gtk_grid_attach(GTK_GRID(cuadricula), e_edad, 1, 3, 1, 1);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    mostrar_con_fundido(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Mascota m;"""
NUEVO_B = r"""    gtk_grid_attach(GTK_GRID(cuadricula), e_edad, 1, 3, 1, 1);

    /* Foto (opcional) */
    GtkWidget *prev_foto = gtk_image_new_from_icon_name("camera-photo", GTK_ICON_SIZE_DIALOG);
    GtkWidget *btn_foto_reg = gtk_button_new_with_label("Elegir foto... (opcional)");
    GtkWidget *caja_foto_reg = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    gtk_box_pack_start(GTK_BOX(caja_foto_reg), prev_foto, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(caja_foto_reg), btn_foto_reg, FALSE, FALSE, 0);
    gtk_grid_attach(GTK_GRID(cuadricula), gtk_label_new("Foto:"), 0, 4, 1, 1);
    gtk_grid_attach(GTK_GRID(cuadricula), caja_foto_reg, 1, 4, 1, 1);
    GtkWidget *ref_foto[2] = { prev_foto, dialogo };
    g_signal_connect(btn_foto_reg, "clicked", G_CALLBACK(on_elegir_foto_mascota_clicked), ref_foto);

    gtk_container_add(GTK_CONTAINER(area), cuadricula);
    mostrar_con_fundido(dialogo);

    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Mascota m;"""

# C: guardar la foto despues de registrar
ANCLA_C2 = r"""        } else if (mascota_agregar(&m) == 0) {
            cargar_mascotas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Mascota registrada correctamente.", FALSE);"""
NUEVO_C2 = r"""        } else if (mascota_agregar(&m) == 0) {
            const char *foto_b64 = (const char *)g_object_get_data(G_OBJECT(prev_foto), "foto_base64");
            gboolean foto_fallo = FALSE;
            if (foto_b64 && foto_b64[0]) {
                int nuevo_id = 0;
                if (mascota_ultimo_id(m.nombre, m.fecha_ingreso, &nuevo_id) != 0 ||
                    mascota_guardar_foto(nuevo_id, foto_b64) != 0)
                    foto_fallo = TRUE;
            }
            cargar_mascotas(ctx);
            if (foto_fallo)
                mostrar_mensaje(GTK_WINDOW(ctx->ventana),
                    "Mascota registrada, pero no se pudo guardar la foto.\nUsa el boton Foto para intentarlo de nuevo.", TRUE);
            else
                mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Mascota registrada correctamente.", FALSE);"""

# D: handler del boton "Foto" (antes de on_cambiar_estado_clicked)
ANCLA_D = r"""static void on_cambiar_estado_clicked(GtkButton *boton, gpointer datos) {"""
NUEVO_D = r"""static void foto_mascota_refrescar_vista(GtkWidget *imagen, GtkWidget *etiqueta, int id) {
    char *b64 = NULL;
    GdkPixbuf *pb = NULL;
    if (mascota_obtener_foto(id, &b64) == 0 && b64) pb = foto_pixbuf_desde_base64(b64);
    free(b64);
    if (pb) {
        GdkPixbuf *v = foto_escalar(pb, 300);
        gtk_image_set_from_pixbuf(GTK_IMAGE(imagen), v);
        gtk_label_set_text(GTK_LABEL(etiqueta), "");
        g_object_unref(v);
        g_object_unref(pb);
    } else {
        gtk_image_set_from_icon_name(GTK_IMAGE(imagen), "camera-photo", GTK_ICON_SIZE_DIALOG);
        gtk_label_set_text(GTK_LABEL(etiqueta), "Esta mascota todavia no tiene foto.");
    }
}

/* Ver / cambiar la foto de la mascota seleccionada. El voluntario solo ve. */
static void on_foto_mascota_clicked(GtkButton *boton, gpointer datos) {
    (void)boton;
    ContextoMascotas *ctx = (ContextoMascotas *)datos;

    int id;
    if (!obtener_id_seleccionado(ctx->treeview, COL_M_ID, &id)) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Selecciona primero una mascota de la lista.", TRUE);
        return;
    }
    GtkTreeSelection *sel = gtk_tree_view_get_selection(GTK_TREE_VIEW(ctx->treeview));
    GtkTreeModel *modelo;
    GtkTreeIter iter;
    gchar *nombre = NULL;
    if (gtk_tree_selection_get_selected(sel, &modelo, &iter))
        gtk_tree_model_get(modelo, &iter, COL_M_NOMBRE, &nombre, -1);

    char titulo[160];
    snprintf(titulo, sizeof(titulo), "Foto de %s", nombre ? nombre : "la mascota");
    GtkWidget *dialogo = gtk_dialog_new_with_buttons(
        titulo, GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL, NULL, NULL);
    if (ctx->rol != ROL_VOLUNTARIO)
        gtk_dialog_add_button(GTK_DIALOG(dialogo), "Cambiar foto...", 1);
    gtk_dialog_add_button(GTK_DIALOG(dialogo), "Cerrar", GTK_RESPONSE_CLOSE);

    GtkWidget *area = gtk_dialog_get_content_area(GTK_DIALOG(dialogo));
    GtkWidget *caja = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_container_set_border_width(GTK_CONTAINER(caja), 12);
    GtkWidget *imagen = gtk_image_new();
    GtkWidget *etiqueta = gtk_label_new("");
    gtk_box_pack_start(GTK_BOX(caja), imagen, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(caja), etiqueta, FALSE, FALSE, 0);
    gtk_container_add(GTK_CONTAINER(area), caja);
    foto_mascota_refrescar_vista(imagen, etiqueta, id);
    mostrar_con_fundido(dialogo);

    int resp;
    while ((resp = gtk_dialog_run(GTK_DIALOG(dialogo))) == 1) {
        char *ruta = elegir_imagen_ruta(GTK_WINDOW(dialogo));
        if (!ruta) continue;
        gchar *b64 = foto_archivo_a_base64(ruta, 300, NULL);
        g_free(ruta);
        if (!b64) {
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo leer esa imagen.", TRUE);
            continue;
        }
        if (mascota_guardar_foto(id, b64) == 0)
            foto_mascota_refrescar_vista(imagen, etiqueta, id);
        else
            mostrar_mensaje(GTK_WINDOW(dialogo), "No se pudo guardar la foto.", TRUE);
        g_free(b64);
    }
    gtk_widget_destroy(dialogo);
    g_free(nombre);
}

static void on_cambiar_estado_clicked(GtkButton *boton, gpointer datos) {"""

# E: crear el boton
ANCLA_E = r"""    GtkWidget *btn_estado    = gtk_button_new_with_label("Cambiar estado");"""
NUEVO_E = r"""    GtkWidget *btn_foto      = gtk_button_new_with_label("Foto");
    GtkWidget *btn_estado    = gtk_button_new_with_label("Cambiar estado");"""

# F: empaquetar el boton (antes de Cambiar estado)
ANCLA_F = r"""    gtk_box_pack_start(GTK_BOX(fila_botones), btn_estado, FALSE, FALSE, 0);"""
NUEVO_F = r"""    gtk_box_pack_start(GTK_BOX(fila_botones), btn_foto, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(fila_botones), btn_estado, FALSE, FALSE, 0);"""

# G: conectar la senal
ANCLA_G = r"""    g_signal_connect(btn_estado, "clicked", G_CALLBACK(on_cambiar_estado_clicked), ctx);"""
NUEVO_G = r"""    g_signal_connect(btn_foto, "clicked", G_CALLBACK(on_foto_mascota_clicked), ctx);
    g_signal_connect(btn_estado, "clicked", G_CALLBACK(on_cambiar_estado_clicked), ctx);"""

CAMBIOS = [
    (DB_H, ANCLA_H, NUEVO_H, "declaracion mascota_buscar_por_id"),
    (DB_C, ANCLA_C, NUEVO_C, "inicio de Vacunas en db.c"),
    (GTK_C, ANCLA_A, NUEVO_A, "on_registrar_clicked"),
    (GTK_C, ANCLA_B, NUEVO_B, "grid del formulario de registro"),
    (GTK_C, ANCLA_C2, NUEVO_C2, "registro correcto de mascota"),
    (GTK_C, ANCLA_D, NUEVO_D, "on_cambiar_estado_clicked"),
    (GTK_C, ANCLA_E, NUEVO_E, "boton Cambiar estado"),
    (GTK_C, ANCLA_F, NUEVO_F, "pack del boton Cambiar estado"),
    (GTK_C, ANCLA_G, NUEVO_G, "senal del boton Cambiar estado"),
]


def main():
    contenidos = {}
    for ruta in (DB_H, DB_C, GTK_C):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if "mascota_guardar_foto" in contenidos[DB_H]:
        print("Este parche ya fue aplicado (db.h ya tiene mascota_guardar_foto). No se cambio nada.")
        sys.exit(0)

    # Validar TODOS los anclajes antes de tocar nada
    for ruta, ancla, _nuevo, nombre in CAMBIOS:
        n = contenidos[ruta].count(ancla)
        if n != 1:
            print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1).")
            print("       No se cambio nada.")
            sys.exit(1)

    for ruta in (DB_H, DB_C, GTK_C):
        shutil.copy(ruta, ruta + ".bak_foto_mascotas")
        print(f"Backup: {ruta}.bak_foto_mascotas")

    for ruta, ancla, nuevo, nombre in CAMBIOS:
        contenidos[ruta] = contenidos[ruta].replace(ancla, nuevo, 1)

    for ruta in (DB_H, DB_C, GTK_C):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenidos[ruta])
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Recuerda crear la columna en SQL Server (si no existe):")
    print("  ALTER TABLE mascotas ADD foto_base64 VARCHAR(MAX) NULL;")
    print("Luego compila:  make")


if __name__ == "__main__":
    main()
