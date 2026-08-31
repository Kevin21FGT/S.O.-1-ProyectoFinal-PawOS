#!/usr/bin/env python3
"""
separar-binario-producto.py

Hace que "make gui" y "make gui-producto" generen dos archivos
DISTINTOS en vez de pisarse el uno al otro:

  make gui           -> pawos-refugio-gui            (version del curso)
  make gui-producto  -> pawos-refugio-gui-producto    (version para el .deb)

Asi pueden existir los dos compilados al mismo tiempo en la carpeta
del repo, sin que compilar uno borre el otro.

Requisito: correr DESPUES de agregar-asistente-bienvenida.py.

Uso: parado en la raiz del repo:
    python3 separar-binario-producto.py

Hace backup antes de tocar el Makefile, y aborta sin cambiar nada si
el texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO = "Makefile"

ANCLA_VAR = """GUI_BIN = pawos-refugio-gui"""
NUEVO_VAR = """GUI_BIN = pawos-refugio-gui
GUI_PRODUCTO_BIN = pawos-refugio-gui-producto"""

ANCLA_TARGETS = """gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

# Variante para el instalador .deb ("vender el programa" - ver
# construir-deb.sh): no siembra las cuentas fijas admin_refugio/
# veterinario1/voluntario1. En su lugar, la primera vez que se abre
# el programa se muestra un asistente para crear el Administrador con
# una contrasena propia. La version del curso ("make gui" normal) no
# cambia en nada.
gui-producto: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) -DPAWOS_SIN_SEMILLA $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

clean-gui:
\trm -f $(GUI_BIN)

.PHONY: gui gui-producto clean-gui"""
NUEVO_TARGETS = """gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

# Variante para el instalador .deb ("vender el programa" - ver
# construir-deb.sh): no siembra las cuentas fijas admin_refugio/
# veterinario1/voluntario1. En su lugar, la primera vez que se abre
# el programa se muestra un asistente para crear el Administrador con
# una contrasena propia. La version del curso ("make gui" normal) no
# cambia en nada. Genera un binario CON OTRO NOMBRE
# (pawos-refugio-gui-producto) para que las dos versiones puedan
# existir compiladas al mismo tiempo sin pisarse.
gui-producto: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c
\t$(CC) $(CFLAGS) -DPAWOS_SIN_SEMILLA $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c -o $(GUI_PRODUCTO_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt

clean-gui:
\trm -f $(GUI_BIN) $(GUI_PRODUCTO_BIN)

.PHONY: gui gui-producto clean-gui"""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    for ancla, nombre in [(ANCLA_VAR, "variable GUI_BIN"), (ANCLA_TARGETS, "targets gui/gui-producto")]:
        if contenido.count(ancla) != 1:
            print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
            print("       Puede que agregar-asistente-bienvenida.py no se haya aplicado todavia,")
            print("       o que el Makefile ya haya sido modificado. No se cambio nada.")
            sys.exit(1)

    contenido = contenido.replace(ANCLA_VAR, NUEVO_VAR, 1)
    contenido = contenido.replace(ANCLA_TARGETS, NUEVO_TARGETS, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak2")
    print(f"Backup creado: {ARCHIVO}.bak2")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} actualizado OK.")
    print("")
    print("Ahora:  make clean-gui && make gui && make gui-producto")
    print("Deben quedar DOS archivos: pawos-refugio-gui y pawos-refugio-gui-producto")


if __name__ == "__main__":
    main()
