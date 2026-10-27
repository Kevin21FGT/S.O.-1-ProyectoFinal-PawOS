#!/usr/bin/env python3
"""
parche-respaldo-seleccion.py   (despues de parche-archivos-fotos-mascotas.py)

PawOS Archivos -> "Respaldar datos ahora": antes de respaldar abre una lista
con casillas para ELEGIR que respaldar:

    Mascotas, Vacunas, Adopciones, Donantes, Alertas de sensores, Clientes,
    Notas del veterinario, Fotos de las mascotas, Base local de usuarios.

Todo viene marcado por defecto (igual que antes). Se puede respaldar una sola
tabla. Si se marca una sola cosa, el nombre sugerido de la carpeta la incluye
(ej. Respaldo_mascotas_2026-10-27_10-30). El mensaje final solo informa lo
que se eligio. No agrega botones: usa el mismo boton y el mismo clic derecho.

Uso (parado en la raiz del repo):
    python3 parche-respaldo-seleccion.py
    make archivos-gui && ./pawos-archivos-gui
"""

import shutil
import sys

ARCHIVO = "src/main_archivos_gui.c"
MARCA = "sel_fotos"

A1 = r"""    strftime(sugerido, sizeof(sugerido), "Respaldo_%Y-%m-%d_%H-%M", &tmv);
"""
N1 = r"""    strftime(sugerido, sizeof(sugerido), "Respaldo_%Y-%m-%d_%H-%M", &tmv);

    /* Que respaldar. Todo marcado = igual que antes. */
    gboolean sel[N_TABLAS_RESPALDO];
    gboolean sel_fotos = TRUE, sel_sqlite = TRUE;
    int n_sel_tablas = 0;
    {
        static const char *const nombres_bonitos[] = {
            "Mascotas", "Vacunas", "Adopciones", "Donantes",
            "Alertas de sensores", "Clientes", "Notas del veterinario"
        };
        GtkWidget *dlg_sel = gtk_dialog_new_with_buttons(
            "Que quieres respaldar?", GTK_WINDOW(ctx->ventana), GTK_DIALOG_MODAL,
            "_Cancelar", GTK_RESPONSE_CANCEL, "_Continuar", GTK_RESPONSE_OK, NULL);
        GtkWidget *area_sel = gtk_dialog_get_content_area(GTK_DIALOG(dlg_sel));
        GtkWidget *caja_sel = gtk_box_new(GTK_ORIENTATION_VERTICAL, 6);
        gtk_container_set_border_width(GTK_CONTAINER(caja_sel), 14);
        GtkWidget *lbl_sel = gtk_label_new(
            "Marca lo que quieres incluir.\nCon todo marcado se respalda todo, como siempre.");
        gtk_widget_set_halign(lbl_sel, GTK_ALIGN_START);
        gtk_box_pack_start(GTK_BOX(caja_sel), lbl_sel, FALSE, FALSE, 4);
        GtkWidget *chk_tabla[N_TABLAS_RESPALDO];
        for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
            chk_tabla[i] = gtk_check_button_new_with_label(
                i < 7 ? nombres_bonitos[i] : TABLAS_RESPALDO[i].tabla);
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(chk_tabla[i]), TRUE);
            gtk_box_pack_start(GTK_BOX(caja_sel), chk_tabla[i], FALSE, FALSE, 0);
        }
        GtkWidget *chk_fotos_w = gtk_check_button_new_with_label("Fotos de las mascotas (archivos .jpg)");
        GtkWidget *chk_sqlite_w = gtk_check_button_new_with_label("Base local de usuarios del personal (SQLite)");
        gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(chk_fotos_w), TRUE);
        gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(chk_sqlite_w), TRUE);
        gtk_box_pack_start(GTK_BOX(caja_sel), chk_fotos_w, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(caja_sel), chk_sqlite_w, FALSE, FALSE, 0);
        gtk_container_add(GTK_CONTAINER(area_sel), caja_sel);
        gtk_widget_show_all(dlg_sel);

        for (;;) {
            if (gtk_dialog_run(GTK_DIALOG(dlg_sel)) != GTK_RESPONSE_OK) {
                gtk_widget_destroy(dlg_sel);
                return;
            }
            n_sel_tablas = 0;
            for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
                sel[i] = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(chk_tabla[i]));
                if (sel[i]) n_sel_tablas++;
            }
            sel_fotos = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(chk_fotos_w));
            sel_sqlite = gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(chk_sqlite_w));
            if (n_sel_tablas + (sel_fotos ? 1 : 0) + (sel_sqlite ? 1 : 0) > 0) break;
            mostrar_mensaje(GTK_WINDOW(dlg_sel), "Marca al menos una opcion.", TRUE);
        }
        gtk_widget_destroy(dlg_sel);

        /* Una sola cosa elegida: el nombre sugerido la incluye. */
        int total_sel = n_sel_tablas + (sel_fotos ? 1 : 0) + (sel_sqlite ? 1 : 0);
        if (total_sel == 1) {
            const char *que = "usuarios";
            if (n_sel_tablas == 1) {
                for (int i = 0; i < N_TABLAS_RESPALDO; i++) if (sel[i]) que = TABLAS_RESPALDO[i].tabla;
            } else if (sel_fotos) {
                que = "fotos";
            }
            char fecha_sug[32];
            strftime(fecha_sug, sizeof(fecha_sug), "%Y-%m-%d_%H-%M", &tmv);
            snprintf(sugerido, sizeof(sugerido), "Respaldo_%s_%s", que, fecha_sug);
        }
    }
"""

A2 = r"""    for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
        csvs[i] = TABLAS_RESPALDO[i].generar();
        if (!csvs[i]) { fallo = TABLAS_RESPALDO[i].tabla; break; }
        leidas++;
    }
    if (fallo) {
        for (int i = 0; i < leidas; i++) g_string_free(csvs[i], TRUE);"""
N2 = r"""    for (int i = 0; i < N_TABLAS_RESPALDO; i++) {
        csvs[i] = NULL;
        if (!sel[i]) { leidas++; continue; }
        csvs[i] = TABLAS_RESPALDO[i].generar();
        if (!csvs[i]) { fallo = TABLAS_RESPALDO[i].tabla; break; }
        leidas++;
    }
    if (fallo) {
        for (int i = 0; i < leidas; i++) if (csvs[i]) g_string_free(csvs[i], TRUE);"""

A3 = r"""        (void)sello;
"""
N3 = r"""        (void)sello;
        if (!csvs[i]) continue;
"""

A4 = r"""        fotos_exportadas = exportar_fotos_mascotas(dir_fotos);"""
N4 = r"""        fotos_exportadas = sel_fotos ? exportar_fotos_mascotas(dir_fotos) : -1;"""

A5 = r"""    int sqlite_ok = (archivos_respaldar_bd_auto() == 0);"""
N5 = r"""    int sqlite_ok = sel_sqlite ? (archivos_respaldar_bd_auto() == 0) : -1;"""

A6 = r"""    g_string_append_printf(msg, "- Archivos CSV en Backups/%s: %d de %d\n", carpeta, locales, N_TABLAS_RESPALDO);"""
N6 = r"""    if (n_sel_tablas > 0)
        g_string_append_printf(msg, "- Archivos CSV en Backups/%s: %d de %d\n", carpeta, locales, n_sel_tablas);"""

A7 = r"""    g_string_append_printf(msg, "- Copia en SmarterASP (tabla respaldos): %d de %d\n", remotos, N_TABLAS_RESPALDO);"""
N7 = r"""    if (n_sel_tablas > 0)
        g_string_append_printf(msg, "- Copia en SmarterASP (tabla respaldos): %d de %d\n", remotos, n_sel_tablas);"""

A8 = r"""    g_string_append_printf(msg, "- Base local de usuarios (SQLite): %s", sqlite_ok ? "copiada" : "no se pudo copiar");"""
N8 = r"""    if (sqlite_ok >= 0)
        g_string_append_printf(msg, "- Base local de usuarios (SQLite): %s", sqlite_ok ? "copiada" : "no se pudo copiar");"""

A9 = r"""    if (remotos < N_TABLAS_RESPALDO) {"""
N9 = r"""    if (n_sel_tablas > 0 && remotos < n_sel_tablas) {"""

A10 = r"""        locales < N_TABLAS_RESPALDO && remotos < N_TABLAS_RESPALDO);"""
N10 = r"""        n_sel_tablas > 0 && locales < n_sel_tablas && remotos < n_sel_tablas);"""

CAMBIOS = [
    (A1, N1, "nombre sugerido del respaldo"),
    (A2, N2, "lectura de las tablas"),
    (A3, N3, "escritura de CSV"),
    (A4, N4, "exportar fotos"),
    (A5, N5, "copia del SQLite"),
    (A6, N6, "mensaje CSV"),
    (A7, N7, "mensaje SmarterASP"),
    (A8, N8, "mensaje SQLite"),
    (A9, N9, "aviso de tabla respaldos"),
    (A10, N10, "condicion de error del mensaje"),
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

    if "exportar_fotos_mascotas" not in contenido:
        print("ERROR: falta el respaldo de fotos. Aplica primero parche-archivos-fotos-mascotas.py.")
        sys.exit(1)

    for ancla, _n, nombre in CAMBIOS:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: '{nombre}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_respaldo_seleccion")
    print(f"Backup: {ARCHIVO}.bak_respaldo_seleccion")
    for ancla, nuevo, _nombre in CAMBIOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")
    print("Listo. Compila:  make archivos-gui && ./pawos-archivos-gui")


if __name__ == "__main__":
    main()
