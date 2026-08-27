#!/bin/bash
# continuar-disco-nuevo.sh - Termina lo que dejo a medias
# usar-disco-nuevo.sh (se atoro en pawos.transfer).
set -e

LBCFG=~/S.O.-1-ProyectoFinal-PawOS/live-build-config
cd "$LBCFG"

echo "=== que es pawos.transfer ==="
file pawos.transfer 2>/dev/null || true
ls -la pawos.transfer

# el mkdir -p del script anterior dejo una carpeta vacia en el disco
# nuevo con este nombre, hay que quitarla de en medio primero
rmdir /mnt/build/pawos.transfer 2>/dev/null || true

if [ -d pawos.transfer ] && [ ! -L pawos.transfer ]; then
  echo "=== es un directorio, moviendo contenido al disco nuevo ==="
  mkdir -p /mnt/build/pawos.transfer
  sudo rsync -a pawos.transfer/ /mnt/build/pawos.transfer/
  sudo rm -rf pawos.transfer
  ln -s /mnt/build/pawos.transfer pawos.transfer
elif [ -f pawos.transfer ] && [ ! -L pawos.transfer ]; then
  echo "=== es un archivo suelto, moviendolo al disco nuevo ==="
  sudo mv pawos.transfer /mnt/build/pawos.transfer
  ln -s /mnt/build/pawos.transfer pawos.transfer
elif [ -L pawos.transfer ]; then
  echo "ya es un symlink, no hace falta hacer nada"
else
  echo "no existe pawos.transfer, revisando si hace falta symlink"
  ln -sf /mnt/build/pawos.transfer pawos.transfer
fi

echo ""
echo "=== verificando estado final de las 4 carpetas ==="
ls -la "$LBCFG" | grep -E "chroot|cache|binary|transfer"

echo ""
echo "--- espacio disco viejo (sda, raiz del sistema) ---"
df -h /
echo "--- espacio disco nuevo (sdc, /mnt/build) ---"
df -h /mnt/build

echo "=== LISTO ==="
