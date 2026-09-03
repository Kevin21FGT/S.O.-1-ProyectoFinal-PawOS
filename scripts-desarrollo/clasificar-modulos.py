#!/usr/bin/env python3
"""
clasificar-modulos.py

Reorganiza src/ e include/ por MODULO: cada .c queda junto a su .h en su
propia subcarpeta (por ejemplo db.c y db.h -> src/db/), en vez de tener
todos los .c sueltos en src/ y todos los .h sueltos en include/. Asi, si
algo falla, se sabe de inmediato en que carpeta buscar.

Que SI se mueve (pares .c/.h, agrupados por modulo):
    db, auth, procesos, memoria, archivos, integridad (+ checksum.h y
    checksum.asm, que son parte de integridad), ui, pantallas,
    pantalla_login, pantalla_procesos, pantalla_memoria,
    pantalla_archivos

Que NO se mueve (se quedan donde estan):
    src/main.c, src/main_gtk.c, src/servidor_monitoreo.c,
    src/vacunas_demonio.c  (son los "programas" que USAN los modulos,
    no un modulo en si)
    include/version.h (un solo archivo suelto, sin .c, se deja igual)

Ajusta automaticamente TODOS los #include afectados (unos 40 en total)
y el Makefile (las listas de archivos fuente y el CFLAGS, que ahora
tambien lleva -Isrc para que "db/db.h", "auth/auth.h", etc. se
encuentren desde cualquier archivo).

Uso: parado en la raiz del repo, con el arbol de trabajo LIMPIO (sin
cambios pendientes -- corre "git status" antes para confirmar):
    python3 clasificar-modulos.py

Hace todo con "git mv" (se conserva el historial de cada archivo) y
aborta sin cambiar nada si algun texto esperado no aparece exactamente
como se espera en algun archivo.
"""

import subprocess
import sys
import os

# ---------------------------------------------------------------
# 1) Ediciones de contenido (ANTES de mover nada, sobre las rutas
#    actuales). Cada tupla es (archivo, [(texto_viejo, texto_nuevo), ...])
# ---------------------------------------------------------------

EDICIONES = [
    ("src/db.c", [
        ('#include "../include/db.h"', '#include "db.h"'),
    ]),
    ("src/integridad.c", [
        ('#include "../include/integridad.h"', '#include "integridad.h"'),
        ('#include "../include/checksum.h"', '#include "checksum.h"'),
        ('#include "../include/db.h"', '#include "db/db.h"'),
    ]),
    ("src/pantallas.c", [
        ('#include "../include/pantallas.h"', '#include "pantallas.h"'),
        ('#include "../include/ui.h"', '#include "ui/ui.h"'),
        ('#include "../include/db.h"', '#include "db/db.h"'),
        ('#include "../include/integridad.h"', '#include "integridad/integridad.h"'),
    ]),
    ("src/pantalla_login.c", [
        ('#include "db.h"', '#include "db/db.h"'),
    ]),
    ("src/auth.c", [
        ('#include "../include/auth.h"', '#include "auth.h"'),
    ]),
    ("src/main.c", [
        ('#include "../include/db.h"', '#include "db/db.h"'),
        ('#include "../include/ui.h"', '#include "ui/ui.h"'),
        ('#include "../include/auth.h"', '#include "auth/auth.h"'),
        ('#include "../include/pantallas.h"', '#include "pantallas/pantallas.h"'),
        ('#include "../include/pantalla_procesos.h"', '#include "pantalla_procesos/pantalla_procesos.h"'),
        ('#include "../include/pantalla_memoria.h"', '#include "pantalla_memoria/pantalla_memoria.h"'),
        ('#include "../include/memoria.h"', '#include "memoria/memoria.h"'),
        ('#include "../include/pantalla_login.h"', '#include "pantalla_login/pantalla_login.h"'),
        ('#include "../include/archivos.h"', '#include "archivos/archivos.h"'),
        ('#include "../include/pantalla_archivos.h"', '#include "pantalla_archivos/pantalla_archivos.h"'),
    ]),
    ("src/pantalla_procesos.c", [
        ('#include "procesos.h"', '#include "procesos/procesos.h"'),
    ]),
    ("src/servidor_monitoreo.c", [
        ('#include "db.h"', '#include "db/db.h"'),
    ]),
    ("src/memoria.c", [
        ('#include "../include/memoria.h"', '#include "memoria.h"'),
    ]),
    ("src/vacunas_demonio.c", [
        ('#include "../include/db.h"', '#include "db/db.h"'),
    ]),
    ("src/archivos.c", [
        ('#include "../include/archivos.h"', '#include "archivos.h"'),
    ]),
    ("src/pantalla_memoria.c", [
        ('#include "memoria.h"', '#include "memoria/memoria.h"'),
    ]),
    ("src/main_gtk.c", [
        ('#include "../include/db.h"', '#include "db/db.h"'),
        ('#include "../include/auth.h"', '#include "auth/auth.h"'),
        ('#include "../include/procesos.h"', '#include "procesos/procesos.h"'),
        ('#include "../include/memoria.h"', '#include "memoria/memoria.h"'),
    ]),
    ("src/pantalla_archivos.c", [
        ('#include "../include/pantalla_archivos.h"', '#include "pantalla_archivos.h"'),
        ('#include "../include/archivos.h"', '#include "archivos/archivos.h"'),
        ('#include "../include/ui.h"', '#include "ui/ui.h"'),
    ]),
    ("src/ui.c", [
        ('#include "../include/ui.h"', '#include "ui.h"'),
    ]),
    ("include/pantalla_memoria.h", [
        ('#include "auth.h"', '#include "auth/auth.h"'),
    ]),
    ("include/pantalla_procesos.h", [
        ('#include "auth.h"', '#include "auth/auth.h"'),
    ]),
    ("include/pantalla_login.h", [
        ('#include "auth.h"', '#include "auth/auth.h"'),
    ]),
    ("include/pantalla_archivos.h", [
        ('#include "auth.h"', '#include "auth/auth.h"'),
    ]),
    ("include/pantallas.h", [
        ('#include "auth.h"', '#include "auth/auth.h"'),
    ]),
]

# ---------------------------------------------------------------
# 2) Movimientos (DESPUES de las ediciones de arriba)
# ---------------------------------------------------------------

MOVIMIENTOS = [
    ("src/db.c", "src/db/db.c"),
    ("include/db.h", "src/db/db.h"),

    ("src/auth.c", "src/auth/auth.c"),
    ("include/auth.h", "src/auth/auth.h"),

    ("src/procesos.c", "src/procesos/procesos.c"),
    ("include/procesos.h", "src/procesos/procesos.h"),

    ("src/memoria.c", "src/memoria/memoria.c"),
    ("include/memoria.h", "src/memoria/memoria.h"),

    ("src/archivos.c", "src/archivos/archivos.c"),
    ("include/archivos.h", "src/archivos/archivos.h"),

    ("src/integridad.c", "src/integridad/integridad.c"),
    ("include/integridad.h", "src/integridad/integridad.h"),
    ("include/checksum.h", "src/integridad/checksum.h"),
    ("src/checksum.asm", "src/integridad/checksum.asm"),

    ("src/ui.c", "src/ui/ui.c"),
    ("include/ui.h", "src/ui/ui.h"),

    ("src/pantallas.c", "src/pantallas/pantallas.c"),
    ("include/pantallas.h", "src/pantallas/pantallas.h"),

    ("src/pantalla_login.c", "src/pantalla_login/pantalla_login.c"),
    ("include/pantalla_login.h", "src/pantalla_login/pantalla_login.h"),

    ("src/pantalla_procesos.c", "src/pantalla_procesos/pantalla_procesos.c"),
    ("include/pantalla_procesos.h", "src/pantalla_procesos/pantalla_procesos.h"),

    ("src/pantalla_memoria.c", "src/pantalla_memoria/pantalla_memoria.c"),
    ("include/pantalla_memoria.h", "src/pantalla_memoria/pantalla_memoria.h"),

    ("src/pantalla_archivos.c", "src/pantalla_archivos/pantalla_archivos.c"),
    ("include/pantalla_archivos.h", "src/pantalla_archivos/pantalla_archivos.h"),
]

# ---------------------------------------------------------------
# 3) Makefile
# ---------------------------------------------------------------

MAKEFILE_EDICIONES = [
    ('CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude',
     'CFLAGS  = -Wall -Wextra -std=c11 -D_DEFAULT_SOURCE -Iinclude -Isrc'),
    ('SRC = src/main.c src/db.c src/ui.c src/auth.c src/pantallas.c src/procesos.c '
     'src/pantalla_procesos.c src/memoria.c src/pantalla_memoria.c src/pantalla_login.c '
     'src/archivos.c src/pantalla_archivos.c src/integridad.c',
     'SRC = src/main.c src/db/db.c src/ui/ui.c src/auth/auth.c src/pantallas/pantallas.c '
     'src/procesos/procesos.c src/pantalla_procesos/pantalla_procesos.c src/memoria/memoria.c '
     'src/pantalla_memoria/pantalla_memoria.c src/pantalla_login/pantalla_login.c '
     'src/archivos/archivos.c src/pantalla_archivos/pantalla_archivos.c src/integridad/integridad.c'),
    ('ASM_SRC = src/checksum.asm', 'ASM_SRC = src/integridad/checksum.asm'),
    ('DEMONIO_SRC = src/vacunas_demonio.c src/db.c', 'DEMONIO_SRC = src/vacunas_demonio.c src/db/db.c'),
    ('MONITOR_SRC = src/servidor_monitoreo.c src/db.c', 'MONITOR_SRC = src/servidor_monitoreo.c src/db/db.c'),
    ('gui: src/main_gtk.c src/db.c src/auth.c src/procesos.c src/memoria.c',
     'gui: src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c src/memoria/memoria.c'),
    ('\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db.c src/auth.c src/procesos.c src/memoria.c '
     '-o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt',
     '\t$(CC) $(CFLAGS) $(GTK_CFLAGS) src/main_gtk.c src/db/db.c src/auth/auth.c src/procesos/procesos.c '
     'src/memoria/memoria.c -o $(GUI_BIN) $(GTK_LIBS) -lsqlite3 -lm -lcrypt'),
]


def leer(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def escribir(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)


def aplicar_ediciones(ruta, pares):
    if not os.path.isfile(ruta):
        print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
        sys.exit(1)
    contenido = leer(ruta)
    for viejo, nuevo in pares:
        if contenido.count(viejo) != 1:
            print(f"ERROR: en {ruta} no se encontro (o se encontro mas de una vez) exactamente:")
            print(f"       {viejo!r}")
            print("       No se cambio nada todavia. Puede que el archivo ya haya sido modificado.")
            sys.exit(1)
        contenido = contenido.replace(viejo, nuevo, 1)
    escribir(ruta, contenido)


def git(*args):
    subprocess.run(["git"] + list(args), check=True)


def main():
    if not os.path.isfile("Makefile") or not os.path.isdir("src") or not os.path.isdir("include"):
        print("ERROR: corre este script parado en la raiz del repo (donde estan Makefile, src/, include/).")
        sys.exit(1)

    print("==> Verificando y aplicando cambios de #include (antes de mover nada)...")
    for ruta, pares in EDICIONES:
        aplicar_ediciones(ruta, pares)
        print(f"  ok: {ruta}")

    print("")
    print("==> Verificando y aplicando cambios al Makefile...")
    aplicar_ediciones("Makefile", MAKEFILE_EDICIONES)
    print("  ok: Makefile")

    print("")
    print("==> Moviendo archivos a sus carpetas por modulo (git mv)...")
    for origen, destino in MOVIMIENTOS:
        carpeta = os.path.dirname(destino)
        os.makedirs(carpeta, exist_ok=True)
        if not os.path.isfile(origen):
            print(f"ERROR: se esperaba encontrar {origen} para moverlo a {destino}, pero no existe.")
            print("       Se detiene aqui -- revisa 'git status', puede que ya se haya movido antes.")
            sys.exit(1)
        git("mv", origen, destino)
        print(f"  movido: {origen} -> {destino}")

    print("")
    print("=========================================================")
    print(" Listo. Revisa con: git status")
    print(" Y prueba que compile TODO antes de comitear:")
    print("")
    print("   make clean && make all")
    print("   make clean-gui && make gui")
    print("")
    print(" Si todo compila bien, comitea con:")
    print("")
    print("   git add -A")
    print('   git commit -m "Reorganiza src/ e include/ por modulo (cada .c junto a su .h)"')
    print("   git push origin rama-Combinada")
    print("=========================================================")


if __name__ == "__main__":
    main()
