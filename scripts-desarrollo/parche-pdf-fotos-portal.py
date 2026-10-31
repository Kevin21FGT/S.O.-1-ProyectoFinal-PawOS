#!/usr/bin/env python3
"""
parche-pdf-fotos-portal.py

Portal de Clientes: los PDF ahora llevan la FOTO de las mascotas.
  - Carnet de vacunas: paginas nuevas "Mis mascotas" (foto circular + nombre)
    entre el frente y el registro de vacunas.
  - Comprobante de solicitudes: seccion "Mascotas" con sus fotos debajo de
    la tabla.
Las mascotas sin foto salen con un circulo con su inicial. El comprobante
de donaciones no cambia.

Requiere reinstalar el generador de PDF (trae el soporte de fotos):
    sudo bash instalar-documentos.sh

Uso (parado en la raiz del repo):
    python3 parche-pdf-fotos-portal.py
    make portal-clientes && ./pawos-portal-clientes
"""

import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"
MARCA = "agregar_fotos_mascotas"

ANCLA_FUNC = r"""static void generar_y_ofrecer_pdf(ContextoApp *ctx, TipoPdf tipo) {"""
NUEVO_FUNC = r"""/* Por cada mascota distinta de las filas (la 1a celda es el nombre) agrega
 * --mascota-foto "Nombre=/tmp/foto.jpg" (ruta vacia si no tiene foto).
 * `a_liberar` guarda los textos de los argumentos y `temporales` las rutas
 * de las fotos, que el que llama debe borrar al terminar. */
static void agregar_fotos_mascotas(GPtrArray *argv, GPtrArray *filas,
                                   GPtrArray *a_liberar, GPtrArray *temporales) {
    Mascota *ms = NULL;
    int n = 0;
    if (mascota_listar(&ms, &n) != 0) return;
    GPtrArray *vistos = g_ptr_array_new_with_free_func(g_free);
    for (guint i = 0; i < filas->len; i++) {
        const char *fila = g_ptr_array_index(filas, i);
        const char *barra = strchr(fila, '|');
        gchar *nombre = barra ? g_strndup(fila, (gsize)(barra - fila)) : g_strdup(fila);
        gboolean repetido = (nombre[0] == '\0');
        for (guint k = 0; !repetido && k < vistos->len; k++)
            if (strcmp(g_ptr_array_index(vistos, k), nombre) == 0) repetido = TRUE;
        if (repetido) { g_free(nombre); continue; }
        g_ptr_array_add(vistos, nombre);

        int id = -1;
        for (int j = 0; j < n; j++)
            if (strcmp(ms[j].nombre, nombre) == 0) { id = ms[j].id; break; }

        gchar *ruta_tmp = NULL;
        if (id >= 0) {
            char *b64 = NULL;
            if (mascota_obtener_foto(id, &b64) == 0 && b64 && b64[0]) {
                gsize largo = 0;
                guchar *bytes = g_base64_decode(b64, &largo);
                gchar *candidata = g_strdup_printf("%s/pawos_mascota_%d_%d.jpg",
                                                   g_get_tmp_dir(), (int)getpid(), id);
                if (largo > 0 && g_file_set_contents(candidata, (const gchar *)bytes, (gssize)largo, NULL))
                    ruta_tmp = candidata;
                else
                    g_free(candidata);
                g_free(bytes);
            }
            free(b64);
        }
        gchar *arg = g_strdup_printf("%s=%s", nombre, ruta_tmp ? ruta_tmp : "");
        g_ptr_array_add(argv, (gpointer)"--mascota-foto");
        g_ptr_array_add(argv, arg);
        g_ptr_array_add(a_liberar, arg);
        if (ruta_tmp) g_ptr_array_add(temporales, ruta_tmp);
    }
    g_ptr_array_free(vistos, TRUE);
    free(ms);
}

static void generar_y_ofrecer_pdf(ContextoApp *ctx, TipoPdf tipo) {"""

ANCLA_ARGV = r"""            g_ptr_array_add(argv, NULL);

            gchar *err = NULL;"""
NUEVO_ARGV = r"""            GPtrArray *fotos_args = g_ptr_array_new_with_free_func(g_free);
            GPtrArray *fotos_tmp = g_ptr_array_new_with_free_func(g_free);
            if (tipo == PDF_CARNET || tipo == PDF_SOLICITUDES)
                agregar_fotos_mascotas(argv, filas, fotos_args, fotos_tmp);
            g_ptr_array_add(argv, NULL);

            gchar *err = NULL;"""

ANCLA_FIN = r"""            if (foto_tmp) { g_unlink(foto_tmp); g_free(foto_tmp); }"""
NUEVO_FIN = r"""            for (guint k = 0; k < fotos_tmp->len; k++) g_unlink(g_ptr_array_index(fotos_tmp, k));
            g_ptr_array_free(fotos_tmp, TRUE);
            g_ptr_array_free(fotos_args, TRUE);
            if (foto_tmp) { g_unlink(foto_tmp); g_free(foto_tmp); }"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de generar_y_ofrecer_pdf"),
    (ANCLA_ARGV, NUEVO_ARGV, "cierre de los argumentos del PDF"),
    (ANCLA_FIN, NUEVO_FIN, "limpieza de la foto temporal"),
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

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_pdf_fotos")
    print(f"Backup: {ARCHIVO}.bak_pdf_fotos")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Recuerda reinstalar el generador:  sudo bash instalar-documentos.sh")
    print("Luego compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
