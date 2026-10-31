#!/usr/bin/env python3
"""
parche-portal-fotos-catalogo.py

Muestra la FOTO de cada mascota en la pestana "Mascotas en adopcion" del
Portal de Clientes (miniatura cuadrada de 64 px a la izquierda del nombre).
Las mascotas sin foto salen con el espacio en blanco. No se quita nada:
solo se agrega una columna.

Uso (parado en la raiz del repo):
    python3 parche-portal-fotos-catalogo.py
    make portal-clientes && ./pawos-portal-clientes
"""

import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"

CAMBIOS = [
    # 1) columna nueva en el enum
    ("""    COL_CAT_INGRESO,
    N_COLUMNAS_CATALOGO""",
     """    COL_CAT_INGRESO,
    COL_CAT_FOTO,
    N_COLUMNAS_CATALOGO""",
     "enum del catalogo"),

    # 2) funcion auxiliar para la miniatura
    ("""static void cargar_catalogo(ContextoApp *ctx) {""",
     """#define FOTO_MINIATURA_SIZE 64

/* Baja la foto (base64) de una mascota y la devuelve como miniatura cuadrada.
 * Devuelve NULL si no tiene foto o no se pudo leer. */
static GdkPixbuf *miniatura_mascota(int mascota_id) {
    char *b64 = NULL;
    if (mascota_obtener_foto(mascota_id, &b64) != 0 || !b64 || b64[0] == '\\0') {
        free(b64);
        return NULL;
    }
    gsize largo = 0;
    guchar *datos = g_base64_decode(b64, &largo);
    free(b64);
    if (!datos || largo == 0) {
        g_free(datos);
        return NULL;
    }
    GdkPixbufLoader *loader = gdk_pixbuf_loader_new();
    GdkPixbuf *resultado = NULL;
    if (gdk_pixbuf_loader_write(loader, datos, largo, NULL) &&
        gdk_pixbuf_loader_close(loader, NULL)) {
        GdkPixbuf *pix = gdk_pixbuf_loader_get_pixbuf(loader);
        if (pix) {
            int w = gdk_pixbuf_get_width(pix), h = gdk_pixbuf_get_height(pix);
            int lado = w < h ? w : h;
            GdkPixbuf *sub = gdk_pixbuf_new_subpixbuf(pix, (w - lado) / 2, (h - lado) / 2, lado, lado);
            if (sub) {
                resultado = gdk_pixbuf_scale_simple(sub, FOTO_MINIATURA_SIZE, FOTO_MINIATURA_SIZE,
                                                    GDK_INTERP_BILINEAR);
                g_object_unref(sub);
            }
        }
    }
    g_object_unref(loader);
    g_free(datos);
    return resultado;
}

static void cargar_catalogo(ContextoApp *ctx) {""",
     "inicio de cargar_catalogo"),

    # 3) pedir la foto de cada mascota
    ("""        gchar *edad = g_strdup_printf("%d", ms[i].edad);
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_catalogo, &iter);""",
     """        gchar *edad = g_strdup_printf("%d", ms[i].edad);
        GdkPixbuf *foto = miniatura_mascota(ms[i].id);
        GtkTreeIter iter;
        gtk_list_store_append(ctx->store_catalogo, &iter);""",
     "lectura de foto en el ciclo"),

    ("""            COL_CAT_INGRESO, ms[i].fecha_ingreso,
            -1);
        g_free(edad);""",
     """            COL_CAT_INGRESO, ms[i].fecha_ingreso,
            COL_CAT_FOTO, foto,
            -1);
        if (foto) g_object_unref(foto);
        g_free(edad);""",
     "guardado de la foto en la fila"),

    # 4) tipo de la columna en el store
    ("""        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING);
    GtkWidget *tv_cat = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_catalogo));""",
     """        G_TYPE_INT, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING, G_TYPE_STRING,
        GDK_TYPE_PIXBUF);
    GtkWidget *tv_cat = gtk_tree_view_new_with_model(GTK_TREE_MODEL(ctx->store_catalogo));""",
     "store del catalogo"),

    # 5) columna visual de la foto
    ("""    anadir_columna(tv_cat, "Nombre", COL_CAT_NOMBRE, -1, TRUE);""",
     """    {
        GtkCellRenderer *r_foto = gtk_cell_renderer_pixbuf_new();
        g_object_set(r_foto, "xpad", 6, "ypad", 4, NULL);
        GtkTreeViewColumn *c_foto = gtk_tree_view_column_new_with_attributes(
            "Foto", r_foto, "pixbuf", COL_CAT_FOTO, NULL);
        gtk_tree_view_append_column(GTK_TREE_VIEW(tv_cat), c_foto);
    }
    anadir_columna(tv_cat, "Nombre", COL_CAT_NOMBRE, -1, TRUE);""",
     "columna Foto"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "miniatura_mascota" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_fotos_catalogo")
    print(f"Backup: {ARCHIVO}.bak_fotos_catalogo")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
