#!/usr/bin/env python3
"""
agregar-transicion-campos.py

Agrega una transicion suave (CSS, sin timers ni codigo nuevo en C mas
alla de un color reutilizado) a los campos de texto: al hacer clic o
tabular hasta un campo (entry/textview), el borde cambia suavemente al
verde de marca -- mismo mecanismo que ya usan los botones
("transition: 150ms ease-in-out;"), asi que no agrega logica nueva ni
puede ralentizar el programa (lo resuelve el motor de CSS de GTK, no
un bucle ni un hilo).

Requisito: correr DESPUES de arreglar-barra-titulo.py (usa el bloque
final de aplicar_estilos() que ese script dejo como ancla).

Uso: parado en la raiz del repo:
    python3 agregar-transicion-campos.py
"""

import shutil
import sys

ARCHIVO = "src/main_gtk.c"

# ---------------------------------------------------------------
# 1. Regla CSS de "entry, textview": agrega borde + transicion +
#    color de foco (verde de marca, fijo en ambos modos).
# ---------------------------------------------------------------
ANCLA_CSS = """        /* Dialogos y campos de texto */
        "dialog { background-color: %s; }"
        "entry, textview, textview text { background-color: %s; color: %s; }\","""
NUEVO_CSS = """        /* Dialogos y campos de texto */
        "dialog { background-color: %s; }"
        "entry, textview, textview text {"
        "  background-color: %s; color: %s;"
        "  border: 1px solid %s;"
        "  border-radius: 6px;"
        "  transition: 150ms ease-in-out;"
        "}"
        "entry:focus, textview:focus {"
        "  border-color: #23924B;"
        "}\","""

# ---------------------------------------------------------------
# 2. Argumentos del printf: agrega boton_borde (color de borde ya
#    existente, reutilizado -- no se crea ninguna variable nueva).
# ---------------------------------------------------------------
ANCLA_ARGS = """        fondo_dialogo,
        fondo_dialogo, color_texto);"""
NUEVO_ARGS = """        fondo_dialogo,
        fondo_dialogo, color_texto, boton_borde);"""


def main():
    pares = [
        (ANCLA_CSS, NUEVO_CSS, "regla CSS de entry/textview"),
        (ANCLA_ARGS, NUEVO_ARGS, "argumentos del printf"),
    ]
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, _nuevo, nombre in pares:
        n = contenido.count(ancla)
        if n != 1:
            print(f"ERROR: el bloque '{nombre}' se encontro {n} veces (se esperaba 1).")
            print("       Puede que arreglar-barra-titulo.py no se haya aplicado todavia,")
            print("       o que aplicar_estilos() ya no coincida con lo esperado.")
            print("       No se cambio nada.")
            sys.exit(1)

    for ancla, nuevo, _nombre in pares:
        contenido = contenido.replace(ancla, nuevo, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak11")
    print(f"Backup creado: {ARCHIVO}.bak11")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: transicion de foco agregada a los campos de texto.")

    print("")
    print("Ahora recompila:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui")
    print("  ./pawos-refugio-gui")


if __name__ == "__main__":
    main()
