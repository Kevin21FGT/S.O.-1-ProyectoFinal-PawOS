#!/usr/bin/env python3
"""
parche-reportes-pdf.py   (necesita pawos-generar-pdf-reporte.py en la raiz del repo)

Reportes -> "Guardar como (.txt / .pdf)...": cuando se elige PDF, ahora se
usa pawos-generar-pdf-reporte.py (encabezado verde, tarjetas con totales,
tablas por mes con subtotales, total final, paginacion). Si el script no esta
instalado o falla, se usa el PDF simple de antes (no se pierde nada).

Tambien agrega el script a construir-deb.sh e instalar-pawos.sh para que se
instale en /usr/local/bin junto a los demas.

Uso (parado en la raiz del repo):
    cp /media/sf_PawOS-Compartido/pawos-generar-pdf-reporte.py .
    python3 parche-reportes-pdf.py
    sudo install -m 755 pawos-generar-pdf-reporte.py /usr/local/bin/
    make gui && ./pawos-refugio-gui
"""

import os
import shutil
import sys

GTK_C = "src/main_gtk.c"
DEB_SH = "construir-deb.sh"
INST_SH = "instalar-pawos.sh"
MARCA = "generar_pdf_reporte_bonito"
SCRIPT = "pawos-generar-pdf-reporte.py"

G_A1 = "static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {"
G_N1 = r"""/* Usa pawos-generar-pdf-reporte.py (fpdf2) para un PDF con diseno. Devuelve
 * FALSE si el script no esta o falla; en ese caso se usa escribir_pdf_simple. */
static gboolean generar_pdf_reporte_bonito(const char *ruta_pdf, const char *contenido) {
    const char *candidatos[] = {
        "/usr/local/bin/pawos-generar-pdf-reporte.py",
        "./pawos-generar-pdf-reporte.py",
        NULL
    };
    const char *script = NULL;
    for (int i = 0; candidatos[i]; i++) {
        if (g_file_test(candidatos[i], G_FILE_TEST_IS_REGULAR)) { script = candidatos[i]; break; }
    }
    if (!script) return FALSE;

    gchar *ruta_tmp = NULL;
    GError *err = NULL;
    int fd = g_file_open_tmp("pawos-reporte-XXXXXX.txt", &ruta_tmp, &err);
    if (fd < 0) { if (err) g_error_free(err); return FALSE; }
    g_close(fd, NULL);

    gboolean ok = FALSE;
    if (g_file_set_contents(ruta_tmp, contenido, -1, NULL)) {
        gchar *argv[] = { "python3", (gchar *)script, "--entrada", ruta_tmp,
                          "--salida", (gchar *)ruta_pdf, NULL };
        gint estado = -1;
        GError *err2 = NULL;
        if (g_spawn_sync(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, NULL, &estado, &err2)
            && estado == 0 && g_file_test(ruta_pdf, G_FILE_TEST_IS_REGULAR))
            ok = TRUE;
        if (err2) g_error_free(err2);
    }
    remove(ruta_tmp);
    g_free(ruta_tmp);
    return ok;
}

static void on_generar_reporte_clicked(GtkButton *boton, gpointer datos) {"""

G_A2 = "        ok = escribir_pdf_simple(ruta_final, contenido_reporte);"
G_N2 = ("        ok = generar_pdf_reporte_bonito(ruta_final, contenido_reporte)\n"
        "             || escribir_pdf_simple(ruta_final, contenido_reporte);")

DEB_A = 'install -m 755 pawos-generar-pdf-cita.py         "$RAIZ/usr/local/bin/pawos-generar-pdf-cita.py"'
DEB_N = DEB_A + '\ninstall -m 755 pawos-generar-pdf-reporte.py       "$RAIZ/usr/local/bin/pawos-generar-pdf-reporte.py"'

INST_A = 'install -m 755 "$BINDIR/pawos-generar-pdf-cita.py"           /usr/local/bin/pawos-generar-pdf-cita.py'
INST_N = INST_A + '\ninstall -m 755 "$BINDIR/pawos-generar-pdf-reporte.py"         /usr/local/bin/pawos-generar-pdf-reporte.py'

CAMBIOS = {
    GTK_C: [(G_A1, G_N1, "funcion del PDF con diseno"), (G_A2, G_N2, "llamada de guardar como PDF")],
    DEB_SH: [(DEB_A, DEB_N, "instalacion en construir-deb.sh")],
    INST_SH: [(INST_A, INST_N, "instalacion en instalar-pawos.sh")],
}


def main():
    if not os.path.isfile(SCRIPT):
        print(f"ERROR: falta {SCRIPT} en la raiz del repo. Copialo desde /media/sf_PawOS-Compartido.")
        sys.exit(1)

    contenidos = {}
    for ruta in CAMBIOS:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenidos[ruta] = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre esto desde la raiz del repo.")
            sys.exit(1)

    if MARCA in contenidos[GTK_C]:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ruta, cambios in CAMBIOS.items():
        for ancla, _n, nombre in cambios:
            n = contenidos[ruta].count(ancla)
            if n != 1:
                print(f"ERROR: en {ruta}, '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
                sys.exit(1)

    for ruta, cambios in CAMBIOS.items():
        shutil.copy(ruta, ruta + ".bak_reportes_pdf")
        texto = contenidos[ruta]
        for ancla, nuevo, _nombre in cambios:
            texto = texto.replace(ancla, nuevo, 1)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"{ruta} parchado OK (backup .bak_reportes_pdf)")
    print("Listo. Instala el script y compila:")
    print("  sudo install -m 755 pawos-generar-pdf-reporte.py /usr/local/bin/")
    print("  make gui && ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
