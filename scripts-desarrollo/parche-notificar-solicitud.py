#!/usr/bin/env python3
"""
parche-notificar-solicitud.py

PawOS Refugio: al APROBAR o RECHAZAR una solicitud del Portal se avisa al
cliente automaticamente (en segundo plano, sin trabar la ventana):

  - Aprobada : correo + WhatsApp, con el PDF y el indicador de progreso.
  - Rechazada: solo correo, con el PDF marcado como RECHAZADA.

Usa el script /usr/local/bin/pawos-notificar-solicitud (instalalo antes,
ver abajo). Si no esta instalado, la solicitud igual se resuelve y la
ventana avisa que no se pudo notificar.

Uso (parado en la raiz del repo):
    sudo install -m 755 /media/sf_PawOS-Compartido/pawos-notificar-solicitud /usr/local/bin/
    python3 parche-notificar-solicitud.py
    make gui
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"
MARCA = "notificar_solicitud_resuelta"

ANCLA_FUNC = r"""static void resolver_solicitud_ui(ContextoSolicitudes *sc, int aprobar) {"""
NUEVO_FUNC = r"""/* Avisa al cliente (correo y, si se aprobo, tambien WhatsApp) en segundo plano.
 * Devuelve TRUE si se pudo lanzar el script de notificacion. */
static gboolean notificar_solicitud_resuelta(int sid, int aprobar) {
    SolicitudInfo *lista = NULL;
    int n = 0;
    if (solicitud_listar_todas(&lista, &n) != 0) return FALSE;
    gboolean lanzado = FALSE;
    for (int i = 0; i < n; i++) {
        if (lista[i].id != sid) continue;
        gchar *id_txt = g_strdup_printf("%d", sid);
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
        break;
    }
    free(lista);
    return lanzado;
}

static void resolver_solicitud_ui(ContextoSolicitudes *sc, int aprobar) {"""

ANCLA_OK = r"""        if (solicitud_resolver(sid, mid, aprobar) == 0) {
            cargar_solicitudes_portal(sc);
            mostrar_mensaje(GTK_WINDOW(sc->dialogo),
                aprobar
                    ? "Solicitud aprobada. La mascota quedo \"en proceso\".\nCuando se entregue, usa Registrar adopcion."
                    : "Solicitud rechazada.",
                FALSE);"""
NUEVO_OK = r"""        if (solicitud_resolver(sid, mid, aprobar) == 0) {
            cargar_solicitudes_portal(sc);
            gboolean aviso = notificar_solicitud_resuelta(sid, aprobar);
            gchar *txt_ok = g_strdup_printf("%s\n\n%s",
                aprobar
                    ? "Solicitud aprobada. La mascota quedo \"en proceso\".\nCuando se entregue, usa Registrar adopcion."
                    : "Solicitud rechazada.",
                aviso
                    ? (aprobar ? "Se esta avisando al cliente por correo y WhatsApp (con PDF)."
                               : "Se esta avisando al cliente por correo (con PDF).")
                    : "No se pudo avisar al cliente: falta instalar pawos-notificar-solicitud.");
            mostrar_mensaje(GTK_WINDOW(sc->dialogo), txt_ok, FALSE);
            g_free(txt_ok);"""

CAMBIOS = [
    (ANCLA_FUNC, NUEVO_FUNC, "inicio de resolver_solicitud_ui"),
    (ANCLA_OK, NUEVO_OK, "mensaje tras resolver"),
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
            print("       Verifica que ya aplicaste parche-aprobar-solicitudes.py.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_notificar_solicitud")
    print(f"Backup: {ARCHIVO}.bak_notificar_solicitud")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make gui   y abre ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
