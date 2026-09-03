#!/usr/bin/env python3
"""
arreglar-umask-actualizar.py

Segunda parte del bug de "Buscar Actualizaciones". La primera parte
(arreglar-opt-pawos-src.py) hizo que /opt/pawos-src se cree con
permisos de grupo correctos -- pero eso solo cubre la carpeta en si.
El problema real es que CADA VEZ que "Buscar Actualizaciones" corre
(clona, hace fetch/pull, o compila con make), crea archivos nuevos
adentro (objetos de git, binarios .o, etc). Sin un umask explicito,
esos archivos nuevos heredan permisos segun quien los creo (ej. 644,
solo el dueno puede escribir), asi que si un usuario clona/actualiza
primero, el SIGUIENTE usuario (otro colaborador, o el mismo usuario
sin sudo) no puede escribir ahi y "Buscar Actualizaciones" vuelve a
fallar con el mismo error generico de conexion.

Fix: agregar "umask 002" al inicio del script pawos-actualizar-gui.
Combinado con el setgid (2775) que ya tiene /opt/pawos-src, esto hace
que TODO lo que el script cree (sin importar que usuario lo corra)
quede escribible para todo el grupo pawos-refugio.

Toca dos copias del mismo script que existen en el repo:
  - pawos-actualizar-gui (la que se instala con instalar-pawos.sh / el .deb)
  - live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui
    (copia para la ISO personalizada; se deja igual por consistencia,
    aunque ese camino ya no se esta usando activamente)

Uso: parado en la raiz del repo:
    python3 arreglar-umask-actualizar.py
"""

import shutil
import sys

ARCHIVOS = [
    "pawos-actualizar-gui",
    "live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui",
]

ANCLA = """# importar que usuario (admin/veterinario/voluntario) lo ejecute.

REPO_URL=$(echo "aHR0cHM6Ly9naXRodWIuY29tL0tldmluMjFGR1QvUy5PLi0xLVByb3llY3RvRmluYWwtUGF3T1MuZ2l0" | base64 -d)"""

NUEVO = """# importar que usuario (admin/veterinario/voluntario) lo ejecute.

# Todo lo que este script cree (copia de git, objetos, binarios
# compilados) debe quedar escribible para todo el grupo pawos-refugio,
# no solo para quien lo corrio -- si no, el siguiente usuario que use
# "Buscar Actualizaciones" no podra escribir ahi y fallara con un
# error generico de conexion.
umask 002

REPO_URL=$(echo "aHR0cHM6Ly9naXRodWIuY29tL0tldmluMjFGR1QvUy5PLi0xLVByb3llY3RvRmluYWwtUGF3T1MuZ2l0" | base64 -d)"""


def main():
    contenidos = {}
    for ruta in ARCHIVOS:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        if contenido.count(ANCLA) != 1:
            print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque esperado.")
            print("       No se cambio nada.")
            sys.exit(1)
        contenidos[ruta] = contenido

    for ruta in ARCHIVOS:
        contenido = contenidos[ruta].replace(ANCLA, NUEVO, 1)
        shutil.copy(ruta, ruta + ".bak")
        print(f"Backup creado: {ruta}.bak")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. Ahora instala la copia corregida y arregla lo ya clonado:")
    print("")
    print("  sudo cp pawos-actualizar-gui /usr/local/bin/pawos-actualizar-gui")
    print("  sudo chmod 755 /usr/local/bin/pawos-actualizar-gui")
    print("  sudo chmod -R g+w /opt/pawos-src")


if __name__ == "__main__":
    main()
