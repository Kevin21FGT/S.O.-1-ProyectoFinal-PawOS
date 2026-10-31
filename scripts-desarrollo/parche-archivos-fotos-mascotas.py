#!/usr/bin/env python3
"""
parche-archivos-fotos-mascotas.py

PawOS Archivos: fotos de las mascotas como archivos, SIN botones nuevos.

  1) "Respaldar datos ahora" (boton o clic derecho): ademas de los CSV, deja
     las fotos en  Backups/<respaldo>/fotos_mascotas/<id>_<nombre>.jpg
     y lo cuenta en el mensaje final.
  2) Clic derecho dentro de la categoria Mascotas -> "Exportar fotos de
     mascotas aqui": crea la carpeta fotos_mascotas en la carpeta abierta
     con una imagen .jpg por mascota (las que tienen foto).

Las fotos siguen viviendo en la BD de SmarterASP (columna foto_base64); esto
solo saca copias a archivos. No se quita nada de lo anterior.

Uso (parado en la raiz del repo):
    python3 parche-archivos-fotos-mascotas.py
    make archivos-gui && ./pawos-archivos-gui   (o el nombre de tu binario)
"""

import shutil
import sys

ARCHIVO = "src/main_archivos_gui.c"
MARCA = "exportar_fotos_mascotas"

# ------------------------------------------------------------ 1) ayudantes (antes del menu)
ANCLA_AYUDA = r"""static void agregar_item_menu(GtkWidget *menu, const char *texto, GCallback cb, ContextoApp *ctx, gboolean activo) {"""
NUEVO_AYUDA = r"""/* Guarda las fotos de las mascotas (JPEG en base64 en la BD) como archivos
 * <id>_<nombre>.jpg dentro de `dir`. La carpeta se crea con la primera foto.
 * Devuelve cuantas se guardaron, o -1 si no se pudo leer la lista. */
static int exportar_fotos_mascotas(const char *dir) {
    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar(&ms, &n) != 0) return -1;
    int guardadas = 0;
    gboolean dir_lista = FALSE;
    for (int i = 0; i < n; i++) {
        char *b64 = NULL;
        if (mascota_obtener_foto(ms[i].id, &b64) != 0 || !b64 || !b64[0]) { free(b64); continue; }
        gsize largo = 0;
        guchar *bytes = g_base64_decode(b64, &largo);
        free(b64);
        if (bytes && largo > 0) {
            if (!dir_lista) dir_lista = (g_mkdir_with_parents(dir, 0770) == 0);
            if (dir_lista) {
                gchar *seguro = g_strdup(ms[i].nombre);
                for (gchar *p = seguro; *p; p++)
                    if ((guchar)*p < 128 && !g_ascii_isalnum(*p)) *p = '_';
                gchar *nombre = g_strdup_printf("%d_%s.jpg", ms[i].id, seguro);
                gchar *ruta = g_build_filename(dir, nombre, NULL);
                if (g_file_set_contents(ruta, (const gchar *)bytes, (gssize)largo, NULL)) guardadas++;
                g_free(ruta);
                g_free(nombre);
                g_free(seguro);
            }
        }
        g_free(bytes);
    }
    free(ms);
    return guardadas;
}

/* Desde el menu se difiere (el menu se destruye al elegir una opcion). */
static gboolean exportar_fotos_diferido(gpointer datos) {
    ContextoApp *ctx = datos;
    gchar *cat = categoria_seleccionada(ctx);
    if (!cat || strcmp(cat, "mascotas") != 0) { g_free(cat); return G_SOURCE_REMOVE; }
    gchar *rel = ruta_relativa_actual(ctx, cat);
    gchar *dir = g_build_filename(archivos_ruta_base(), rel, "fotos_mascotas", NULL);
    int n = exportar_fotos_mascotas(dir);
    if (n < 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana),
            "No se pudieron leer las mascotas (revisa la conexion) o crear la carpeta.", TRUE);
    } else if (n == 0) {
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Ninguna mascota tiene foto todavia.", FALSE);
    } else {
        cargar_archivos(ctx);
        gchar *msg = g_strdup_printf("%d foto%s exportada%s a la carpeta \"fotos_mascotas\".",
                                     n, n == 1 ? "" : "s", n == 1 ? "" : "s");
        mostrar_mensaje(GTK_WINDOW(ctx->ventana), msg, FALSE);
        g_free(msg);
    }
    g_free(dir);
    g_free(rel);
    g_free(cat);
    return G_SOURCE_REMOVE;
}

static void on_exportar_fotos_desde_menu(GtkMenuItem *item, gpointer datos) {
    (void)item;
    g_idle_add(exportar_fotos_diferido, datos);
}

static void agregar_item_menu(GtkWidget *menu, const char *texto, GCallback cb, ContextoApp *ctx, gboolean activo) {"""

# ------------------------------------------------------------ 2) item del menu (solo en Mascotas)
ANCLA_MENU = r"""    agregar_item_menu(menu, "Respaldar datos ahora", G_CALLBACK(on_respaldar_desde_menu), ctx, n == 0);"""
NUEVO_MENU = r"""    agregar_item_menu(menu, "Respaldar datos ahora", G_CALLBACK(on_respaldar_desde_menu), ctx, n == 0);
    {
        gchar *cat_menu = categoria_seleccionada(ctx);
        if (cat_menu && strcmp(cat_menu, "mascotas") == 0)
            agregar_item_menu(menu, "Exportar fotos de mascotas aqui",
                              G_CALLBACK(on_exportar_fotos_desde_menu), ctx, TRUE);
        g_free(cat_menu);
    }"""

# ------------------------------------------------------------ 3) respaldo completo
ANCLA_RESP = r"""    /* 3. Copia del SQLite local (usuarios del personal), como antes. */"""
NUEVO_RESP = r"""    /* 2b. Fotos de las mascotas (archivos .jpg) junto a los CSV */
    int fotos_exportadas = 0;
    {
        gchar *dir_fotos = g_build_filename(archivos_ruta_base(), "backups", carpeta, "fotos_mascotas", NULL);
        fotos_exportadas = exportar_fotos_mascotas(dir_fotos);
        g_free(dir_fotos);
    }

    /* 3. Copia del SQLite local (usuarios del personal), como antes. */"""

ANCLA_MSG = r"""    g_string_append_printf(msg, "- Archivos CSV en Backups/%s: %d de %d\n", carpeta, locales, N_TABLAS_RESPALDO);"""
NUEVO_MSG = r"""    g_string_append_printf(msg, "- Archivos CSV en Backups/%s: %d de %d\n", carpeta, locales, N_TABLAS_RESPALDO);
    if (fotos_exportadas >= 0)
        g_string_append_printf(msg, "- Fotos de mascotas (Backups/%s/fotos_mascotas): %d\n", carpeta, fotos_exportadas);"""

CAMBIOS = [
    (ANCLA_AYUDA, NUEVO_AYUDA, "inicio de agregar_item_menu"),
    (ANCLA_MENU, NUEVO_MENU, "opcion Respaldar datos ahora del menu"),
    (ANCLA_RESP, NUEVO_RESP, "paso 3 del respaldo"),
    (ANCLA_MSG, NUEVO_MSG, "mensaje final del respaldo"),
]


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        print("       (Si el archivo se llama distinto, avisame.)")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_fotos_mascotas")
    print(f"Backup: {ARCHIVO}.bak_fotos_mascotas")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make archivos-gui   y abre PawOS Archivos")


if __name__ == "__main__":
    main()
