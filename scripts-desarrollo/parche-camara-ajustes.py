#!/usr/bin/env python3
"""
parche-camara-ajustes.py

Pulido de la camara en PawOS Refugio (despues de parche-editor-foto-camara.py):
  - Vista previa mas fluida: pide 640x480 a 15 fps y no reescala.
  - Espera de 12 s (antes 5 s) antes de decir "no llega imagen": la webcam
    tarda en arrancar dentro de la VM.
  - Corrige el aviso de GTK "gtk_container_set_border_width ... GtkLabel"
    (la etiqueta del cuadro "De donde quieres tomar la foto?" usaba un
    margen de contenedor; ahora usa margenes propios).
  - Oculta los mensajes de ffmpeg en la terminal (Broken pipe, etc.) y al
    cerrar la camara detiene ffmpeg ANTES de cerrar la tuberia.

Uso (parado en la raiz del repo):
    python3 parche-camara-ajustes.py
    make gui
"""

import shutil
import sys

GTK_C = "src/main_gtk.c"

CAMBIOS = [
    # argumentos de ffmpeg
    (r"""        "ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", dev,
        "-vf", "fps=10,scale=960:-2", "-c:v", "mjpeg", "-q:v", "4",
        "-f", "image2pipe", "-", NULL""",
     r"""        "ffmpeg", "-loglevel", "error", "-fflags", "nobuffer",
        "-f", "v4l2", "-framerate", "15", "-video_size", "640x480", "-i", dev,
        "-vf", "fps=12", "-c:v", "mjpeg", "-q:v", "5",
        "-f", "image2pipe", "-", NULL""",
     "argumentos de ffmpeg"),
    # ocultar stderr de ffmpeg
    (r"""g_spawn_async_with_pipes(NULL, argv, NULL, G_SPAWN_SEARCH_PATH,""",
     r"""g_spawn_async_with_pipes(NULL, argv, NULL,
                                  G_SPAWN_SEARCH_PATH | G_SPAWN_STDERR_TO_DEV_NULL,""",
     "g_spawn de ffmpeg"),
    # espera mas larga + mensaje
    (r"""    c->timeout = g_timeout_add(5000, camara_sin_imagen_cb, c);
    gtk_label_set_text(GTK_LABEL(c->etiqueta), "Conectando con la camara...");""",
     r"""    c->timeout = g_timeout_add(12000, camara_sin_imagen_cb, c);
    gtk_label_set_text(GTK_LABEL(c->etiqueta),
        "Conectando con la camara (puede tardar unos segundos)...");""",
     "espera de la camara"),
    # detener ffmpeg antes de cerrar la tuberia
    (r"""    if (c->canal) {
        g_io_channel_shutdown(c->canal, FALSE, NULL);
        g_io_channel_unref(c->canal);
        c->canal = NULL;
    }
    if (c->activo) {
        kill((pid_t)c->pid, SIGTERM);
        g_spawn_close_pid(c->pid);
        c->activo = FALSE;
    }""",
     r"""    if (c->activo) {
        kill((pid_t)c->pid, SIGTERM);
        g_spawn_close_pid(c->pid);
        c->activo = FALSE;
    }
    if (c->canal) {
        g_io_channel_shutdown(c->canal, FALSE, NULL);
        g_io_channel_unref(c->canal);
        c->canal = NULL;
    }""",
     "camara_detener"),
    # aviso de GTK por el margen de la etiqueta
    (r"""    gtk_container_set_border_width(GTK_CONTAINER(lbl), 18);""",
     r"""    gtk_widget_set_margin_top(lbl, 18);
    gtk_widget_set_margin_bottom(lbl, 18);
    gtk_widget_set_margin_start(lbl, 18);
    gtk_widget_set_margin_end(lbl, 18);""",
     "margen de la etiqueta de origen"),
]


def main():
    try:
        with open(GTK_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {GTK_C}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if "fps=12" in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    for ancla, _nuevo, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            print("       Verifica que ya aplicaste parche-editor-foto-camara.py.")
            sys.exit(1)

    shutil.copy(GTK_C, GTK_C + ".bak_camara_ajustes")
    print(f"Backup: {GTK_C}.bak_camara_ajustes")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(GTK_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{GTK_C} parchado OK.")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
