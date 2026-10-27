#!/usr/bin/env python3
"""
parche-notificar-foto.py   (despues de parche-notificar-solicitud.py)

El aviso de solicitud aprobada/rechazada ahora lleva la FOTO de la mascota
en el PDF. PawOS Refugio baja la foto de la base, la guarda en un archivo
temporal y se la pasa a pawos-notificar-solicitud (que la borra al terminar).

Requiere reinstalar los scripts (traen el soporte de fotos):
    cd /media/sf_PawOS-Compartido && sudo bash instalar-documentos.sh

Uso (parado en la raiz del repo):
    python3 parche-notificar-foto.py
    make gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "pawos_notif_"

ANCLA = r"""        gchar *id_txt = g_strdup_printf("%d", sid);
        gchar *argv[] = {
            "pawos-notificar-solicitud",
            "--estado", aprobar ? "aprobada" : "rechazada",
            "--id", id_txt,
            "--cliente", lista[i].cliente_nombre,
            "--correo", lista[i].cliente_correo,
            "--telefono", lista[i].cliente_telefono,
            "--mascota", lista[i].mascota_nombre,
            "--fecha", lista[i].fecha,
            NULL
        };
        lanzado = g_spawn_async(NULL, argv, NULL,
                                G_SPAWN_SEARCH_PATH | G_SPAWN_STDOUT_TO_DEV_NULL | G_SPAWN_STDERR_TO_DEV_NULL,
                                NULL, NULL, NULL, NULL);
        g_free(id_txt);
        break;"""

NUEVO = r"""        gchar *id_txt = g_strdup_printf("%d", sid);

        /* Foto de la mascota -> archivo temporal (el script lo borra al terminar) */
        gchar *foto_ruta = NULL;
        {
            char *b64 = NULL;
            if (mascota_obtener_foto(lista[i].mascota_id, &b64) == 0 && b64 && b64[0]) {
                gsize largo = 0;
                guchar *bytes = g_base64_decode(b64, &largo);
                gchar *candidata = g_strdup_printf("%s/pawos_notif_%d_%lld.jpg",
                    g_get_tmp_dir(), sid, (long long)g_get_monotonic_time());
                if (largo > 0 && g_file_set_contents(candidata, (const gchar *)bytes, (gssize)largo, NULL))
                    foto_ruta = candidata;
                else
                    g_free(candidata);
                g_free(bytes);
            }
            free(b64);
        }

        GPtrArray *av = g_ptr_array_new();
        g_ptr_array_add(av, (gpointer)"pawos-notificar-solicitud");
        g_ptr_array_add(av, (gpointer)"--estado");   g_ptr_array_add(av, (gpointer)(aprobar ? "aprobada" : "rechazada"));
        g_ptr_array_add(av, (gpointer)"--id");       g_ptr_array_add(av, id_txt);
        g_ptr_array_add(av, (gpointer)"--cliente");  g_ptr_array_add(av, lista[i].cliente_nombre);
        g_ptr_array_add(av, (gpointer)"--correo");   g_ptr_array_add(av, lista[i].cliente_correo);
        g_ptr_array_add(av, (gpointer)"--telefono"); g_ptr_array_add(av, lista[i].cliente_telefono);
        g_ptr_array_add(av, (gpointer)"--mascota");  g_ptr_array_add(av, lista[i].mascota_nombre);
        g_ptr_array_add(av, (gpointer)"--fecha");    g_ptr_array_add(av, lista[i].fecha);
        if (foto_ruta) {
            g_ptr_array_add(av, (gpointer)"--foto-mascota");
            g_ptr_array_add(av, foto_ruta);
        }
        g_ptr_array_add(av, NULL);
        lanzado = g_spawn_async(NULL, (gchar **)av->pdata, NULL,
                                G_SPAWN_SEARCH_PATH | G_SPAWN_STDOUT_TO_DEV_NULL | G_SPAWN_STDERR_TO_DEV_NULL,
                                NULL, NULL, NULL, NULL);
        if (!lanzado && foto_ruta) remove(foto_ruta);
        g_ptr_array_free(av, TRUE);
        g_free(foto_ruta);
        g_free(id_txt);
        break;"""


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

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque de envio aparece {n} veces (debe ser 1). No se cambio nada.")
        print("       Verifica que ya aplicaste parche-notificar-solicitud.py.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_notificar_foto")
    print(f"Backup: {ARCHIVO}.bak_notificar_foto")
    contenido = contenido.replace(ANCLA, NUEVO, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Reinstala los scripts:  cd /media/sf_PawOS-Compartido && sudo bash instalar-documentos.sh")
    print("Luego compila:  make gui")


if __name__ == "__main__":
    main()
