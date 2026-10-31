#!/usr/bin/env python3
"""
parche-camara-nombres.py

Mejora el selector de camara de PawOS Refugio (despues de
parche-editor-foto-camara.py):
  - Muestra el NOMBRE de cada camara ("VirtualBox Webcam - DroidCam Vi
    (/dev/video2)") en vez de solo /dev/videoN.
  - Oculta los nodos que no dan imagen (metadatos: video1, video3...).
  - Si hay una camara DroidCam conectada, la elige por defecto.

Uso (parado en la raiz del repo):
    python3 parche-camara-nombres.py
    make gui
"""

import shutil
import sys

GTK_C = "src/main_gtk.c"

CAMBIOS = [
    (r"""    for (guint i = 0; i < lista->len; i++) {
        gchar *ruta = g_strdup_printf("/dev/%s", (char *)g_ptr_array_index(lista, i));
        gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(combo), ruta);
        g_free(ruta);
    }
    if (lista->len > 0) gtk_combo_box_set_active(GTK_COMBO_BOX(combo), 0);""",
     r"""    gint activo = -1, cuantas = 0;
    for (guint i = 0; i < lista->len; i++) {
        const char *dev = (const char *)g_ptr_array_index(lista, i);

        /* index 0 = nodo de video; index 1+ = metadatos (no dan imagen) */
        gchar *ruta_idx = g_strdup_printf("/sys/class/video4linux/%s/index", dev);
        gchar *idx_txt = NULL;
        gboolean saltar = FALSE;
        if (g_file_get_contents(ruta_idx, &idx_txt, NULL, NULL)) {
            if (atoi(idx_txt) != 0) saltar = TRUE;
            g_free(idx_txt);
        }
        g_free(ruta_idx);
        if (saltar) continue;

        gchar *ruta_nom = g_strdup_printf("/sys/class/video4linux/%s/name", dev);
        gchar *nombre = NULL;
        if (g_file_get_contents(ruta_nom, &nombre, NULL, NULL) && nombre) g_strstrip(nombre);
        g_free(ruta_nom);

        gchar *ruta = g_strdup_printf("/dev/%s", dev);
        gchar *texto = (nombre && nombre[0])
            ? g_strdup_printf("%s (%s)", nombre, ruta)
            : g_strdup(ruta);
        gtk_combo_box_text_append(GTK_COMBO_BOX_TEXT(combo), ruta, texto);
        if (activo < 0 && nombre && strstr(nombre, "DroidCam")) activo = cuantas;
        cuantas++;
        g_free(texto);
        g_free(ruta);
        g_free(nombre);
    }
    if (cuantas > 0) gtk_combo_box_set_active(GTK_COMBO_BOX(combo), activo >= 0 ? activo : 0);""",
     "llenado del combo de camaras"),
    (r"""    gchar *dev = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(c->combo));""",
     r"""    gchar *dev = g_strdup(gtk_combo_box_get_active_id(GTK_COMBO_BOX(c->combo)));""",
     "lectura de la camara elegida"),
]


def main():
    try:
        with open(GTK_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "/sys/class/video4linux/" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            print("       Verifica que ya aplicaste parche-editor-foto-camara.py.")
            sys.exit(1)

    shutil.copy(GTK_C, GTK_C + ".bak_camara_nombres")
    print(f"Backup: {GTK_C}.bak_camara_nombres")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(GTK_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{GTK_C} parchado OK.")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
