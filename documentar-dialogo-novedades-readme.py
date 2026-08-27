#!/usr/bin/env python3
"""
documentar-dialogo-novedades-readme.py

Agrega al README.md (manual tecnico) la explicacion del nuevo dialogo
de novedades (tipo Google Play / Windows Update) que aparece antes de
abrir la terminal del actualizador.

Uso: parado en la raiz del repo (rama-Combinada actualizada):
    python3 documentar-dialogo-novedades-readme.py

Hace backup automatico a README.md.bak antes de tocar nada, y aborta
sin cambiar nada si no encuentra el texto exacto esperado.
"""

import shutil
import sys

ARCHIVO = "README.md"

ANCLA = '''### Diseño "de programa comercial" (sin exponer el repositorio)'''

NUEVO = '''### Dialogo de novedades antes de actualizar (estilo tienda de aplicaciones)

Antes de abrir la terminal del paso anterior, el propio boton "🔄 Buscar Actualizaciones" (`on_actualizar_clicked` en `main_gtk.c`) ya hace una primera revision el mismo, sin necesitar la terminal para eso: corre un `git fetch` + `git log` corto contra `/opt/pawos-src`, y segun el resultado:

- **Sin conexion:** muestra un mensaje de error simple ("revisa tu conexion a internet") y no abre nada mas.
- **Ya esta al dia:** muestra "Ya tienes la ultima version instalada." y termina ahi, sin molestar con una terminal para nada.
- **Hay una version nueva (o es la primera instalacion):** abre un dialogo nativo de GTK con el titulo "PawOS - Actualizaciones", el changelog (un renglon por cada commit nuevo, cada uno con un icono segun de que tipo es — 🔧 correccion/estabilidad, ⭐ mejora, ✨ novedad, detectado por palabras clave en el propio mensaje del commit) y dos botones: "Cancelar" y "Actualizar ahora". Solo si el usuario confirma con "Actualizar ahora" se abre la terminal con `pawos-actualizar-gui` para hacer la descarga/recompilacion real (ver arriba).

La idea es que el usuario final vea de forma clara y agradable que va a cambiar *antes* de comprometerse a actualizar, en vez de encontrarse una terminal en blanco corriendo comandos — el mismo tipo de experiencia que Google Play o Windows Update.

### Diseño "de programa comercial" (sin exponer el repositorio)'''


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print("ERROR: no se encontro (o se encontro mas de una vez) el texto exacto esperado")
        print(f"       en {ARCHIVO}. Puede que el archivo ya haya sido modificado.")
        print("       No se cambio nada.")
        sys.exit(1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak")
    print(f"Backup creado: {ARCHIVO}.bak")

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} actualizado OK.")


if __name__ == "__main__":
    main()
