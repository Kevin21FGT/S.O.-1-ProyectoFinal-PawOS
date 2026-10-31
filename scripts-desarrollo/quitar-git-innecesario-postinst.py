#!/usr/bin/env python3
"""
quitar-git-innecesario-postinst.py

El instalador (.deb) fallaba en cualquier maquina que no tuviera "git"
instalado, con el error:
    /var/lib/dpkg/info/pawos-refugio.postinst: line 25: git: command not found

Esa parte del instalador preparaba una carpeta (/opt/pawos-src) para el
sistema VIEJO de actualizaciones, que clonaba el codigo con git. Ya no
se usa -- el boton "Buscar Actualizaciones" ahora usa
pawos-revisar-version/pawos-actualizar-deb, que no necesitan git para
nada. Esta parte quedo de mas y solo causaba fallos en instalaciones
limpias. Se quita del instalador para que esto no le siga pasando a
nadie mas.

Uso: parado en la raiz del repo:
    python3 quitar-git-innecesario-postinst.py
"""

import shutil
import sys

ARCHIVO = "construir-deb.sh"

ANCLA = '''# Carpeta donde "Buscar Actualizaciones" (pawos-actualizar-gui) clona el
# repositorio. Sin esto, un usuario normal no tiene permiso de crear
# /opt/pawos-src (root:root, 755) y la actualizacion falla en silencio.
mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src

# Marca la carpeta como segura para TODOS los usuarios del equipo
# (escribe en /etc/gitconfig). Sin esto, git rechaza operar ahi con
# "posesion dudosa detectada" porque el dueno es root pero la usan
# usuarios normales -- y ese error se confunde con "sin conexion".
git config --system --add safe.directory /opt/pawos-src
'''
NUEVO = ""


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = contenido.count(ANCLA)
    if n != 1:
        print(f"ERROR: el bloque esperado se encontro {n} veces (se esperaba 1). No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak3")
    print(f"Backup creado: {ARCHIVO}.bak3")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: ya no depende de git para instalarse.")

    print("")
    print("Genera el .deb de nuevo para que este arreglo quede incluido:")
    print("  bash construir-deb.sh")


if __name__ == "__main__":
    main()
