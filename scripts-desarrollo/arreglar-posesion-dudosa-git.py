#!/usr/bin/env python3
"""
arreglar-posesion-dudosa-git.py

Tercera parte del bug de "Buscar Actualizaciones". Las dos partes
anteriores arreglaron los PERMISOS de /opt/pawos-src, pero el boton
"Buscar Actualizaciones" del GUI no usa el script pawos-actualizar-gui
para revisar si hay novedades -- tiene su propio comando git inline
(en on_actualizar_clicked(), src/main_gtk.c) que hace "git fetch"
directo. Ese comando nunca configuraba "safe.directory", asi que git
rechaza operar ahi con:

    fatal: posesion dudosa detectada en el repositorio en '/opt/pawos-src'

porque la carpeta es dueno de "root" (la creo el instalador) pero la
usa un usuario normal. Este error de git se confunde con "no hay
conexion a internet" porque la salida de error esta silenciada.

Fix (dos capas, para que funcione en instalaciones nuevas Y en esta VM
ya instalada):

  1. instalar-pawos.sh y el postinst del .deb (construir-deb.sh) ahora
     marcan /opt/pawos-src como seguro para TODOS los usuarios del
     equipo de una vez (git config --system, escribe en /etc/gitconfig,
     se hace como root durante la instalacion).

  2. Como respaldo, el comando inline dentro de main_gtk.c tambien
     marca la carpeta como segura para el usuario que lo corre (git
     config --global), por si alguien tiene una instalacion vieja de
     antes de este fix y el /etc/gitconfig del punto 1 no se aplico
     todavia.

Requisito: correr DESPUES de arreglar-opt-pawos-src.py (usa el mismo
bloque de /opt/pawos-src como ancla).

Uso: parado en la raiz del repo:
    python3 arreglar-posesion-dudosa-git.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"
ARCHIVO_GTK = "src/main_gtk.c"

DQ = '"'
BS = '\\'

# ---------------------------------------------------------------
# instalar-pawos.sh y construir-deb.sh: agregan la linea de
# safe.directory a nivel de sistema justo despues de crear
# /opt/pawos-src (bloque agregado por arreglar-opt-pawos-src.py).
# ---------------------------------------------------------------
ANCLA_INSTALADORES = """mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src"""
NUEVO_INSTALADORES = """mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src

# Marca la carpeta como segura para TODOS los usuarios del equipo
# (escribe en /etc/gitconfig). Sin esto, git rechaza operar ahi con
# "posesion dudosa detectada" porque el dueno es root pero la usan
# usuarios normales -- y ese error se confunde con "sin conexion".
git config --system --add safe.directory /opt/pawos-src"""

# ---------------------------------------------------------------
# src/main_gtk.c: respaldo por si /etc/gitconfig no tiene la marca
# (instalaciones viejas). Se agrega justo despues de fijar REPO_DIR
# y RAMA, antes de entrar al "if [ -d ... ]".
# Construido con concatenacion explicita (en vez de un bloque
# triple-quoted) para no arriesgar un escape ambiguo: la linea de
# anclaje termina en una comilla suelta pegada al cierre de cadena.
# ---------------------------------------------------------------
_linea1 = "    const gchar *comando ="
_linea2 = "        " + DQ + "bash -c '" + DQ
_linea3 = "        " + DQ + "REPO_DIR=/opt/pawos-src; RAMA=rama-Kevin; " + DQ
_linea4 = "        " + DQ + "if [ -d " + BS + DQ + "$REPO_DIR/.git" + BS + DQ + " ]; then " + DQ

ANCLA_GTK = "\n".join([_linea1, _linea2, _linea3, _linea4])

_linea_safe = ("        " + DQ + "git config --global --add safe.directory "
               + BS + DQ + "$REPO_DIR" + BS + DQ + " 2>/dev/null; " + DQ)

NUEVO_GTK = "\n".join([_linea1, _linea2, _linea3, _linea_safe, _linea4])


def main():
    archivos = [
        (ARCHIVO_INSTALAR, ANCLA_INSTALADORES, NUEVO_INSTALADORES, "bloque /opt/pawos-src"),
        (ARCHIVO_DEB, ANCLA_INSTALADORES, NUEVO_INSTALADORES, "bloque /opt/pawos-src (postinst)"),
        (ARCHIVO_GTK, ANCLA_GTK, NUEVO_GTK, "comando inline de on_actualizar_clicked"),
    ]

    contenidos = {}
    for ruta, ancla, _nuevo, nombre in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el '{nombre}'.")
            print("       Puede que arreglar-opt-pawos-src.py no se haya aplicado todavia,")
            print("       o que el archivo ya haya sido modificado. No se cambio nada.")
            sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, ancla, nuevo, _nombre in archivos:
        contenido = contenidos[ruta].replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak")
        print(f"Backup creado: {ruta}.bak")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Ahora, para desbloquear ESTA VM ya instalada (una sola vez):")
    print("")
    print("  sudo git config --system --add safe.directory /opt/pawos-src")
    print("")
    print("Y para que el binario ya instalado tenga el respaldo del punto 2:")
    print("  make clean-gui && make gui && make gui-producto")


if __name__ == "__main__":
    main()
