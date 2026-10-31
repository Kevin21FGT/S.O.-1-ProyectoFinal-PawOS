/*
 * pawos-foto -- fotos de mascotas desde la terminal (sin abrir la ventana).
 *
 * Usa la MISMA conexion de db.c (~/.pawos_db_config y ~/.pawos_db_remota) y
 * guarda la foto igual que PawOS Refugio: JPEG de maximo 300 px en base64,
 * en la columna mascotas.foto_base64 de SQL Server.
 *
 * Uso:
 *   pawos-foto listar
 *   pawos-foto poner <id> <imagen> [--cuadrada]
 *   pawos-foto ver <id> <salida.jpg>
 *   pawos-foto quitar <id>
 *
 * Compilar (desde la raiz del repo, con este archivo en src/):
 *   gcc -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude -Isrc \
 *       $(pkg-config --cflags gdk-pixbuf-2.0 glib-2.0) \
 *       src/main_foto_cli.c src/db/db.c -o pawos-foto \
 *       $(pkg-config --libs gdk-pixbuf-2.0 glib-2.0) -lsqlite3 -lm -lcrypt -lodbc
 */

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "db/db.h"

#define MAX_LADO 300

static void uso(void) {
    fprintf(stderr,
        "Uso:\n"
        "  pawos-foto listar\n"
        "  pawos-foto poner <id> <imagen> [--cuadrada]\n"
        "  pawos-foto ver <id> <salida.jpg>\n"
        "  pawos-foto quitar <id>\n");
}

static int buscar_mascota(int id, Mascota *m) {
    if (mascota_buscar_por_id(id, m) != 0) {
        fprintf(stderr, "No existe una mascota con id %d (o no hay conexion a la base).\n", id);
        return -1;
    }
    return 0;
}

static int cmd_listar(void) {
    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar(&ms, &n) != 0) {
        fprintf(stderr, "No se pudo leer la lista de mascotas.\n");
        return 1;
    }
    printf("%-4s %-20s %s\n", "ID", "NOMBRE", "FOTO");
    for (int i = 0; i < n; i++) {
        char *b64 = NULL;
        size_t largo = 0;
        if (mascota_obtener_foto(ms[i].id, &b64) == 0 && b64) largo = strlen(b64);
        free(b64);
        if (largo > 0) printf("%-4d %-20s %zu caracteres\n", ms[i].id, ms[i].nombre, largo);
        else           printf("%-4d %-20s (sin foto)\n", ms[i].id, ms[i].nombre);
    }
    free(ms);
    return 0;
}

static int cmd_poner(int id, const char *ruta, int cuadrada) {
    Mascota m;
    if (buscar_mascota(id, &m) != 0) return 1;

    GError *err = NULL;
    GdkPixbuf *orig = gdk_pixbuf_new_from_file(ruta, &err);
    if (!orig) {
        fprintf(stderr, "No se pudo leer la imagen '%s': %s\n", ruta, err ? err->message : "?");
        if (err) g_error_free(err);
        return 1;
    }
    GdkPixbuf *base = gdk_pixbuf_apply_embedded_orientation(orig);
    g_object_unref(orig);
    if (!base) return 1;

    if (gdk_pixbuf_get_has_alpha(base)) {
        GdkPixbuf *plano = gdk_pixbuf_composite_color_simple(
            base, gdk_pixbuf_get_width(base), gdk_pixbuf_get_height(base),
            GDK_INTERP_NEAREST, 255, 1, 0xFFFFFF, 0xFFFFFF);
        g_object_unref(base);
        base = plano;
        if (!base) return 1;
    }

    if (cuadrada) {
        int w = gdk_pixbuf_get_width(base), h = gdk_pixbuf_get_height(base);
        int lado = w < h ? w : h;
        GdkPixbuf *sub = gdk_pixbuf_new_subpixbuf(base, (w - lado) / 2, (h - lado) / 2, lado, lado);
        GdkPixbuf *copia = gdk_pixbuf_copy(sub);
        g_object_unref(sub);
        g_object_unref(base);
        base = copia;
        if (!base) return 1;
    }

    int w = gdk_pixbuf_get_width(base), h = gdk_pixbuf_get_height(base);
    GdkPixbuf *final = base;
    if (w > MAX_LADO || h > MAX_LADO) {
        double f = (double)MAX_LADO / (double)(w > h ? w : h);
        int nw = (int)(w * f), nh = (int)(h * f);
        if (nw < 1) nw = 1;
        if (nh < 1) nh = 1;
        final = gdk_pixbuf_scale_simple(base, nw, nh, GDK_INTERP_BILINEAR);
        g_object_unref(base);
        if (!final) return 1;
    }

    gchar *buf = NULL;
    gsize largo = 0;
    if (!gdk_pixbuf_save_to_buffer(final, &buf, &largo, "jpeg", NULL, "quality", "85", NULL)) {
        fprintf(stderr, "No se pudo convertir la imagen a JPEG.\n");
        g_object_unref(final);
        return 1;
    }
    gchar *b64 = g_base64_encode((const guchar *)buf, largo);
    int rc = mascota_guardar_foto(id, b64);
    if (rc == 0)
        printf("Foto guardada para %s (id %d): %dx%d, %zu caracteres base64.\n",
               m.nombre, id, gdk_pixbuf_get_width(final), gdk_pixbuf_get_height(final), strlen(b64));
    else
        fprintf(stderr, "No se pudo guardar la foto en la base de datos.\n");
    g_free(b64);
    g_free(buf);
    g_object_unref(final);
    return rc == 0 ? 0 : 1;
}

static int cmd_ver(int id, const char *salida) {
    Mascota m;
    if (buscar_mascota(id, &m) != 0) return 1;
    char *b64 = NULL;
    if (mascota_obtener_foto(id, &b64) != 0 || !b64 || !b64[0]) {
        fprintf(stderr, "%s (id %d) no tiene foto.\n", m.nombre, id);
        free(b64);
        return 1;
    }
    gsize largo = 0;
    guchar *datos = g_base64_decode(b64, &largo);
    free(b64);
    if (!datos || largo == 0) {
        fprintf(stderr, "La foto guardada no es base64 valido.\n");
        g_free(datos);
        return 1;
    }
    GError *err = NULL;
    gboolean ok = g_file_set_contents(salida, (const gchar *)datos, (gssize)largo, &err);
    g_free(datos);
    if (!ok) {
        fprintf(stderr, "No se pudo escribir '%s': %s\n", salida, err ? err->message : "?");
        if (err) g_error_free(err);
        return 1;
    }
    printf("Foto de %s (id %d) guardada en %s (%zu bytes).\n", m.nombre, id, salida, (size_t)largo);
    return 0;
}

static int cmd_quitar(int id) {
    Mascota m;
    if (buscar_mascota(id, &m) != 0) return 1;
    if (mascota_guardar_foto(id, "") != 0) {
        fprintf(stderr, "No se pudo quitar la foto.\n");
        return 1;
    }
    printf("Foto de %s (id %d) eliminada.\n", m.nombre, id);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { uso(); return 2; }
    if (strcmp(argv[1], "listar") == 0) return cmd_listar();
    if (strcmp(argv[1], "poner") == 0 && argc >= 4) {
        int cuadrada = (argc >= 5 && strcmp(argv[4], "--cuadrada") == 0);
        return cmd_poner(atoi(argv[2]), argv[3], cuadrada);
    }
    if (strcmp(argv[1], "ver") == 0 && argc >= 4) return cmd_ver(atoi(argv[2]), argv[3]);
    if (strcmp(argv[1], "quitar") == 0 && argc >= 3) return cmd_quitar(atoi(argv[2]));
    uso();
    return 2;
}
