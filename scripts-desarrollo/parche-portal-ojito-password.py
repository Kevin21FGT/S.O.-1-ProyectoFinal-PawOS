#!/usr/bin/env python3
"""
parche-portal-ojito-password.py

Portal de Clientes: icono de "ojito" dentro de los campos de contrasena para
verla (texto) o volver a ocultarla (puntos). Queda en:
  - Inicio de sesion
  - Registro (contrasena y confirmar contrasena)
  - Recuperar contrasena (contrasena nueva y confirmacion)
  - Editar mi perfil (contrasena nueva)
Es el mismo ojito que ya usa PawOS Refugio.

Uso (parado en la raiz del repo):
    python3 parche-portal-ojito-password.py
    make portal-clientes && ./pawos-portal-clientes
"""

import re
import shutil
import sys

ARCHIVO = "src/main_portal_clientes.c"
MARCA = "activar_ojo_password"

ANCLA_FUNC = "static void mostrar_registro(GtkWindow *padre) {"
NUEVO_FUNC = r"""/* Ojito dentro del campo de contrasena: alterna entre puntos y texto. */
static void on_ojo_password(GtkEntry *entrada, GtkEntryIconPosition posicion,
                            GdkEvent *evento, gpointer datos) {
    (void)evento;
    (void)datos;
    if (posicion != GTK_ENTRY_ICON_SECONDARY) return;
    gboolean visible = gtk_entry_get_visibility(entrada);
    gtk_entry_set_visibility(entrada, !visible);
    gtk_entry_set_icon_from_icon_name(entrada, GTK_ENTRY_ICON_SECONDARY,
        !visible ? "view-conceal-symbolic" : "view-reveal-symbolic");
    gtk_entry_set_icon_tooltip_text(entrada, GTK_ENTRY_ICON_SECONDARY,
        !visible ? "Ocultar contrasena" : "Mostrar contrasena");
}

static void activar_ojo_password(GtkWidget *entrada) {
    gtk_entry_set_icon_from_icon_name(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                      "view-reveal-symbolic");
    gtk_entry_set_icon_tooltip_text(GTK_ENTRY(entrada), GTK_ENTRY_ICON_SECONDARY,
                                    "Mostrar contrasena");
    g_signal_connect(entrada, "icon-press", G_CALLBACK(on_ojo_password), NULL);
}

static void mostrar_registro(GtkWindow *padre) {"""

# Despues de cada "gtk_entry_set_visibility(GTK_ENTRY(x), FALSE);" se agrega el ojito.
PATRON = re.compile(r"^([ \t]*)gtk_entry_set_visibility\(GTK_ENTRY\((\w+)\), FALSE\);[ \t]*$", re.MULTILINE)


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

    if contenido.count(ANCLA_FUNC) != 1:
        print(f"ERROR: 'inicio de mostrar_registro' aparece {contenido.count(ANCLA_FUNC)} veces (debe ser 1). No se cambio nada.")
        sys.exit(1)
    campos = PATRON.findall(contenido)
    if not campos:
        print("ERROR: no se encontraron campos de contrasena. No se cambio nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_ojito")
    print(f"Backup: {ARCHIVO}.bak_ojito")

    contenido = contenido.replace(ANCLA_FUNC, NUEVO_FUNC, 1)
    contenido, n = PATRON.subn(
        lambda m: f"{m.group(0)}\n{m.group(1)}activar_ojo_password({m.group(2)});", contenido)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: {n} campos de contrasena con ojito.")
    print("Listo. Compila:  make portal-clientes && ./pawos-portal-clientes")


if __name__ == "__main__":
    main()
