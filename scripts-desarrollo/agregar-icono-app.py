#!/usr/bin/env python3
"""
agregar-icono-app.py

Le pone el logo de PawOS (branding/pawos-icon.png) como icono de todas
las ventanas de la app, en vez del icono generico de GTK:

  1. src/main_gtk.c: en main(), justo despues de gtk_init(), intenta
     primero la ruta instalada (/usr/share/icons/pawos-icon.png, la que
     ya usa el .deb) y si no existe cae al archivo del repo
     (branding/pawos-icon.png, para cuando se corre en desarrollo sin
     instalar). Si ninguna existe, no pasa nada -- se queda con el
     icono generico, igual que antes.

  2. instalar-pawos.sh: el instalador por script (a diferencia del
     .deb) todavia no copiaba el icono a /usr/share/icons/ ni lo
     apuntaba en el lanzador (.desktop) -- este parche agrega ambas
     cosas, igual que ya hace construir-deb.sh.

Uso: parado en la raiz del repo:
    python3 agregar-icono-app.py
"""

import shutil
import sys

ARCHIVO_C = "src/main_gtk.c"
ARCHIVO_SH = "instalar-pawos.sh"

# ---------------------------------------------------------------
# 1. main_gtk.c: icono de la app en main()
# ---------------------------------------------------------------
ANCLA_C = """int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    /* Modo claro/oscuro automatico: se aplica al iniciar segun la
     * preferencia del sistema, y se vuelve a aplicar solo si el usuario
     * cambia esa preferencia mientras PawOS esta abierto. Sin switch
     * propio en la app. */"""
NUEVO_C = """int main(int argc, char **argv) {
    gtk_init(&argc, &argv);

    /* Icono de la app para todas las ventanas: usa la ruta instalada
     * (la que copia el .deb / instalar-pawos.sh) si existe; si no, cae
     * al archivo del repo (cuando se corre en desarrollo, sin
     * instalar). Si ninguna existe no pasa nada -- se queda con el
     * icono generico de GTK, igual que antes. */
    if (g_file_test("/usr/share/icons/pawos-icon.png", G_FILE_TEST_EXISTS)) {
        gtk_window_set_default_icon_from_file("/usr/share/icons/pawos-icon.png", NULL);
    } else if (g_file_test("branding/pawos-icon.png", G_FILE_TEST_EXISTS)) {
        gtk_window_set_default_icon_from_file("branding/pawos-icon.png", NULL);
    }

    /* Modo claro/oscuro automatico: se aplica al iniciar segun la
     * preferencia del sistema, y se vuelve a aplicar solo si el usuario
     * cambia esa preferencia mientras PawOS esta abierto. Sin switch
     * propio en la app. */"""

# ---------------------------------------------------------------
# 2. instalar-pawos.sh: copiar el icono a /usr/share/icons/
# ---------------------------------------------------------------
ANCLA_SH_BIN = """install -m 755 "$BINDIR/pawos-refugio-gui"    /usr/local/bin/pawos-refugio-gui"""
NUEVO_SH_BIN = """install -m 755 "$BINDIR/pawos-refugio-gui"    /usr/local/bin/pawos-refugio-gui

echo "=== 3a. Instalando el icono de la app ==="
mkdir -p /usr/share/icons
[ -f "$BINDIR/branding/pawos-icon.png" ] && install -m 644 "$BINDIR/branding/pawos-icon.png" /usr/share/icons/pawos-icon.png"""

# ---------------------------------------------------------------
# 3. instalar-pawos.sh: apuntar el .desktop al icono real
# ---------------------------------------------------------------
ANCLA_SH_DESKTOP = """Exec=/usr/local/bin/pawos-refugio-gui
Terminal=false
Icon=utilities-terminal
Categories=Utility;
EOF"""
NUEVO_SH_DESKTOP = """Exec=/usr/local/bin/pawos-refugio-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF"""


def parchar(archivo, pares, sufijo_bak):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {archivo}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: en {archivo}, el bloque '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(archivo, archivo + sufijo_bak)
    print(f"Backup creado: {archivo}{sufijo_bak}")
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{archivo} parchado OK.")


def main():
    parchar(ARCHIVO_C, [(ANCLA_C, NUEVO_C, "icono en main()")], ".bak14")
    parchar(
        ARCHIVO_SH,
        [
            (ANCLA_SH_BIN, NUEVO_SH_BIN, "copiar icono a /usr/share/icons"),
            (ANCLA_SH_DESKTOP, NUEVO_SH_DESKTOP, "Icon= del .desktop"),
        ],
        ".bak2",
    )

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  sudo mkdir -p /usr/share/icons && sudo cp branding/pawos-icon.png /usr/share/icons/pawos-icon.png")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
