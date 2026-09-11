#!/usr/bin/env python3
"""
arreglar-opt-pawos-src.py

Bug real (encontrado en vivo): el boton "Buscar Actualizaciones"
(pawos-actualizar-gui) clona el repositorio en /opt/pawos-src, pero
ningun instalador creaba esa carpeta de antemano. Como /opt es de
root:root con permisos 755, un usuario normal (admin/veterinario/
voluntario) no tiene permiso de crear ahi una carpeta nueva, asi que
"git clone" fallaba en silencio (la salida de error esta redirigida a
/dev/null) y el usuario solo veia "no se pudo descargar PawOS. Revisa
tu conexion a internet" -- un mensaje enganoso, el problema real eran
los permisos.

Fix: instalar-pawos.sh y el postinst del .deb (construir-deb.sh) ahora
crean /opt/pawos-src de antemano con dueno root:pawos-refugio y
permisos 2775 (setgid), igual que /var/pawos. Asi cualquier usuario
del grupo pawos-refugio puede clonar/actualizar ahi sin sudo.

Uso: parado en la raiz del repo:
    python3 arreglar-opt-pawos-src.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"

BLOQUE_OPT_PAWOS_SRC = """
# Carpeta donde "Buscar Actualizaciones" (pawos-actualizar-gui) clona el
# repositorio. Sin esto, un usuario normal no tiene permiso de crear
# /opt/pawos-src (root:root, 755) y la actualizacion falla en silencio.
mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src"""

# ---------------------------------------------------------------
# instalar-pawos.sh
# ---------------------------------------------------------------
ANCLA_INSTALAR = """echo "=== 6. Creando /var/pawos y permisos ==="
mkdir -p /var/pawos/reportes
chown -R root:pawos-refugio /var/pawos
chmod -R 2770 /var/pawos"""
NUEVO_INSTALAR = ANCLA_INSTALAR + "\n" + BLOQUE_OPT_PAWOS_SRC

# ---------------------------------------------------------------
# construir-deb.sh (dentro del heredoc del DEBIAN/postinst)
# ---------------------------------------------------------------
ANCLA_DEB = """mkdir -p /var/pawos/reportes
chown -R root:pawos-refugio /var/pawos
chmod -R 2770 /var/pawos

# A quien instalo el paquete"""
NUEVO_DEB = "mkdir -p /var/pawos/reportes\nchown -R root:pawos-refugio /var/pawos\nchmod -R 2770 /var/pawos\n" + BLOQUE_OPT_PAWOS_SRC + "\n\n# A quien instalo el paquete"


def main():
    archivos = [
        (ARCHIVO_INSTALAR, ANCLA_INSTALAR, NUEVO_INSTALAR, "bloque /var/pawos"),
        (ARCHIVO_DEB, ANCLA_DEB, NUEVO_DEB, "bloque /var/pawos (postinst)"),
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
            print("       No se cambio nada.")
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
    print("Listo. No hace falta recompilar (son scripts de instalacion, no codigo C).")
    print("Si quieres reconstruir el .deb con el fix: bash construir-deb.sh")


if __name__ == "__main__":
    main()
