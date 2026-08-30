#!/usr/bin/env python3
# agregar-novedades-primera-vez.py
#
# El "Buscar Actualizaciones" ya mostraba las novedades (mensajes de
# commits) cuando actualizaba una copia existente, pero no decia nada
# en una instalacion de PRIMERA VEZ (git clone desde cero), porque ahi
# no hay version anterior contra la cual comparar. Este parche agrega
# un resumen de los ultimos commits tambien en ese caso, para que se
# vea igual de completo.
#
# Parcha las 3 copias del script dentro de live-build-config (la que
# se usa como fuente para el ISO), ademas de la copia suelta en la
# raiz del repo si existe. Hace backup .bak y aborta sin escribir nada
# si no encuentra el bloque esperado.

import shutil
import sys
import os

VIEJO = '''else
  echo "Descargando por primera vez (puede tardar un momento)..."
  if ! git clone --branch "$RAMA" "$REPO_URL" "$REPO_DIR" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: no se pudo descargar PawOS. Revisa tu conexion a internet."
    echo "(Si el problema persiste, puede que falten permisos en /opt/pawos-src)"
    read -p "Presiona Enter para cerrar..."
    exit 1
  fi
  cd "$REPO_DIR" || exit 1
fi'''

NUEVO = '''else
  echo "Descargando por primera vez (puede tardar un momento)..."
  if ! git clone --branch "$RAMA" "$REPO_URL" "$REPO_DIR" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: no se pudo descargar PawOS. Revisa tu conexion a internet."
    echo "(Si el problema persiste, puede que falten permisos en /opt/pawos-src)"
    read -p "Presiona Enter para cerrar..."
    exit 1
  fi
  cd "$REPO_DIR" || exit 1

  echo ""
  echo "Version instalada (ultimos cambios incluidos):"
  git log -10 --pretty=format:"  - %s"
  echo ""
fi'''

def parchar(ruta):
    if not os.path.isfile(ruta):
        print(f"  (no existe {ruta}, se omite)")
        return
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()

    if "ultimos cambios incluidos" in contenido:
        print(f"  [{ruta}] ya estaba aplicado, se omite.")
        return
    if VIEJO not in contenido:
        print(f"ERROR [{ruta}]: no se encontro el bloque esperado. No se modifico nada.")
        sys.exit(1)

    contenido = contenido.replace(VIEJO, NUEVO, 1)
    shutil.copyfile(ruta, ruta + ".bak")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"  [{ruta}] parchado OK (backup en {ruta}.bak)")


for ruta in [
    "pawos-actualizar-gui",
    "live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui",
]:
    parchar(ruta)

print("")
print("Listo.")
