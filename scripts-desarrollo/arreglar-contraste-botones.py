#!/usr/bin/env python3
"""
arreglar-contraste-botones.py

Bug: los botones "genericos" (los que no tienen clase .modulo, .salir
ni .cat-* -- por ejemplo "Salir"/"Soy Colaborador"/"Soy Cliente" del
dialogo de login) nunca tenian fondo propio en la hoja de estilos.
Antes, como el modo oscuro nunca se detectaba (ver
arreglar-modo-oscuro-automatico.py), el texto oscuro por defecto se
leia bien sobre el fondo claro por defecto del boton. Ahora que el
modo oscuro si se activa correctamente, el texto se vuelve claro pero
el fondo del boton se queda igual (claro) -- texto claro sobre fondo
claro, casi invisible.

Este parche le da a "button {}" un fondo/texto/borde propio segun el
modo (con su propio :hover), sin afectar los botones que ya tienen
color fijo (.modulo, .cat-refugio/gestion/sistema, .salir siguen
ganando por ser selectores mas especificos, la cascada de CSS los deja
intactos).

Requisito: correr DESPUES de arreglar-modo-oscuro-automatico.py (usa
los valores de fondo ya actualizados como ancla).

Uso: parado en la raiz del repo:
    python3 arreglar-contraste-botones.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. Nuevas variables de color para los botones genericos
# ---------------------------------------------------------------
ANCLA_VARS = """    const char *deshabilitado_bg = oscuro ? "#3A423B" : "#CBD3C7";
    const char *deshabilitado_fg = oscuro ? "#8B948B" : "#7C877A";

    gchar *css = g_strdup_printf("""
NUEVO_VARS = """    const char *deshabilitado_bg = oscuro ? "#3A423B" : "#CBD3C7";
    const char *deshabilitado_fg = oscuro ? "#8B948B" : "#7C877A";
    const char *boton_bg         = oscuro ? "#2A322B" : "#FFFFFF";
    const char *boton_bg_hover   = oscuro ? "#354039" : "#F2F3F5";
    const char *boton_fg         = oscuro ? "#E7ECE4" : "#1C2620";
    const char *boton_borde      = oscuro ? "#3A443B" : "#D7DEDA";

    gchar *css = g_strdup_printf("""

# ---------------------------------------------------------------
# 2. La regla "button {}" generica: le agrega fondo/texto/borde propio
# ---------------------------------------------------------------
ANCLA_CSS_BOTON = """        /* Botones generales */
        "button {"
        "  padding: 10px;"
        "  border-radius: 10px;"
        "  transition: 150ms ease-in-out;"
        "}"
        "button.modulo {\""""
NUEVO_CSS_BOTON = """        /* Botones generales (los que no tienen .modulo/.salir/.cat-* --
         * necesitan su propio fondo/texto segun el modo, si no el texto
         * queda invisible sobre un fondo que nunca cambia). */
        "button {"
        "  padding: 10px;"
        "  border-radius: 10px;"
        "  transition: 150ms ease-in-out;"
        "  background-color: %s;"
        "  color: %s;"
        "  border: 1px solid %s;"
        "}"
        "button:hover { background-color: %s; }"
        "button.modulo {\""""

# ---------------------------------------------------------------
# 3. Lista de argumentos del printf: insertar los 4 nuevos donde
#    corresponde (justo donde va la regla "button {}" en el texto).
# ---------------------------------------------------------------
ANCLA_ARGS = """        fondo_ventana, color_texto,
        deshabilitado_bg, deshabilitado_fg,"""
NUEVO_ARGS = """        fondo_ventana, color_texto,
        boton_bg, boton_fg, boton_borde, boton_bg_hover,
        deshabilitado_bg, deshabilitado_fg,"""


def main():
    pares = [
        (ANCLA_VARS, NUEVO_VARS, "declaracion de variables de color"),
        (ANCLA_CSS_BOTON, NUEVO_CSS_BOTON, "regla CSS button{}"),
        (ANCLA_ARGS, NUEVO_ARGS, "lista de argumentos del printf"),
    ]

    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        if contenido.count(ancla) != 1:
            print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       Puede que arreglar-modo-oscuro-automatico.py no se haya aplicado")
            print("       todavia. No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak7")
    print(f"Backup creado: {ARCHIVO}.bak7")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
