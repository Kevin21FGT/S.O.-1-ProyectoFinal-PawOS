#!/usr/bin/env python3
"""
conectar-envio-recordatorio.py

Ultimo paso: despues de registrar una vacuna CON un Cliente elegido
para notificar, pregunta si se quiere mandar el recordatorio (correo
+ WhatsApp) ya mismo, y si se confirma, abre una terminal que corre
pawos-notificar-cita con los datos de esa cita.

Si no se elige Cliente (el valor por defecto, "(Ninguno)"), todo sigue
exactamente igual que antes -- no se pregunta nada ni se abre nada.

Requisito: correr DESPUES de agregar-selector-cliente-vacunas.py (usa
el bloque que ese script dejo como ancla).

Uso: parado en la raiz del repo:
    python3 conectar-envio-recordatorio.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

ANCLA = """
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));
        const gchar *cliente_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_cliente));
        v.cliente_id = cliente_id_texto ? atoi(cliente_id_texto) : 0;

        if (vacuna_agregar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna registrada.", FALSE);
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la vacuna.", TRUE);
        }
    }
    free(lista_clientes_vac);
    gtk_widget_destroy(dialogo);
}"""
NUEVO = """
    if (gtk_dialog_run(GTK_DIALOG(dialogo)) == GTK_RESPONSE_OK) {
        Vacuna v;
        memset(&v, 0, sizeof(v));
        v.mascota_id = mascota_id;
        snprintf(v.nombre_vacuna, sizeof(v.nombre_vacuna), "%s", gtk_entry_get_text(GTK_ENTRY(e_nombre)));
        snprintf(v.fecha_aplicacion, sizeof(v.fecha_aplicacion), "%s", gtk_entry_get_text(GTK_ENTRY(e_aplic)));
        snprintf(v.fecha_proxima, sizeof(v.fecha_proxima), "%s", gtk_entry_get_text(GTK_ENTRY(e_prox)));
        snprintf(v.observaciones, sizeof(v.observaciones), "%s", gtk_entry_get_text(GTK_ENTRY(e_obs)));
        const gchar *cliente_id_texto = gtk_combo_box_get_active_id(GTK_COMBO_BOX(e_cliente));
        v.cliente_id = cliente_id_texto ? atoi(cliente_id_texto) : 0;

        if (vacuna_agregar(&v) == 0) {
            cargar_vacunas(ctx);
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Vacuna registrada.", FALSE);

            /* Si se eligio un Cliente para notificar, se ofrece mandar
             * el recordatorio (PDF por correo y WhatsApp) ya mismo. Si
             * no se eligio ninguno (v.cliente_id == 0), nada de esto
             * corre -- se comporta exactamente igual que antes. */
            if (v.cliente_id > 0) {
                Cliente *cliente_elegido = NULL;
                for (int i = 0; i < n_clientes_vac; i++) {
                    if (lista_clientes_vac[i].id == v.cliente_id) {
                        cliente_elegido = &lista_clientes_vac[i];
                        break;
                    }
                }
                if (cliente_elegido) {
                    gchar *pregunta = g_strdup_printf(
                        "Enviar recordatorio de esta cita a %s por correo y WhatsApp?",
                        cliente_elegido->nombre);
                    GtkWidget *confirmar = gtk_message_dialog_new(
                        GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL, GTK_MESSAGE_QUESTION,
                        GTK_BUTTONS_YES_NO, "%s", pregunta);
                    g_free(pregunta);
                    gint respuesta = gtk_dialog_run(GTK_DIALOG(confirmar));
                    gtk_widget_destroy(confirmar);
                    if (respuesta == GTK_RESPONSE_YES) {
                        gchar *argv_envio[] = {
                            "x-terminal-emulator", "-e", "pawos-notificar-cita",
                            cliente_elegido->correo, cliente_elegido->telefono,
                            cliente_elegido->nombre, m.nombre, v.nombre_vacuna, v.fecha_proxima,
                            NULL
                        };
                        GError *error_envio = NULL;
                        if (!g_spawn_async(NULL, argv_envio, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, NULL, &error_envio)) {
                            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "No se pudo abrir el envio de recordatorio.", TRUE);
                            if (error_envio) g_error_free(error_envio);
                        }
                    }
                }
            }
        } else {
            mostrar_mensaje(GTK_WINDOW(ctx->ventana), "Error al registrar la vacuna.", TRUE);
        }
    }
    free(lista_clientes_vac);
    gtk_widget_destroy(dialogo);
}"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el bloque esperado.")
        print("       Puede que agregar-selector-cliente-vacunas.py no se haya aplicado")
        print("       todavia, o que el archivo ya haya sido modificado. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak4")
    print(f"Backup creado: {ARCHIVO}.bak4")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")

    print("")
    print("Ahora instala pawos-notificar-cita y compila:")
    print("  sudo cp pawos-notificar-cita /usr/local/bin/")
    print("  sudo chmod 755 /usr/local/bin/pawos-notificar-cita")
    print("  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
