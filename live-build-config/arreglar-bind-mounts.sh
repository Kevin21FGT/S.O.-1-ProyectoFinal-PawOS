#!/bin/bash
# arreglar-bind-mounts.sh - Reemplaza los symlinks (que xorriso no
# sigue) por bind mounts de verdad. Preserva el chroot ya compilado
# (movido al disco nuevo) y el binary/ que ya tiene isolinux.bin bien
# copiado.
set -e

LBCFG=~/S.O.-1-ProyectoFinal-PawOS/live-build-config
cd "$LBCFG"

echo "=== 1) moviendo el chroot ya compilado (carpeta real) al disco nuevo ==="
if [ -d "$LBCFG/chroot" ] && [ ! -L "$LBCFG/chroot" ]; then
  echo "  (esto puede tardar un par de minutos, son varios GB)"
  sudo rsync -a --delete "$LBCFG/chroot"/ /mnt/build/chroot/
  sudo rm -rf "$LBCFG/chroot"
else
  echo "  chroot ya no es carpeta real (symlink o no existe), se omite el rsync"
  sudo rm -f "$LBCFG/chroot"
fi
sudo mkdir -p "$LBCFG/chroot"

echo "=== 2) preparando punto de montaje para binary (el contenido bueno ya esta en /mnt/build/binary) ==="
[ -L "$LBCFG/binary" ] && rm "$LBCFG/binary"
sudo mkdir -p "$LBCFG/binary"

echo "=== 3) preparando punto de montaje para cache ==="
if [ -L "$LBCFG/cache" ]; then
  rm "$LBCFG/cache"
fi
sudo mkdir -p "$LBCFG/cache"

echo "=== 4) montando con bind mount de verdad (no symlink) ==="
sudo mount --bind /mnt/build/chroot "$LBCFG/chroot"
sudo mount --bind /mnt/build/binary "$LBCFG/binary"
sudo mount --bind /mnt/build/cache "$LBCFG/cache"

echo ""
echo "=== 5) verificando ==="
mount | grep "S.O.-1-ProyectoFinal-PawOS/live-build-config"
echo "--- primeras entradas del chroot montado ---"
ls "$LBCFG/chroot" | head -5
echo "--- isolinux dentro de binary montado ---"
ls "$LBCFG/binary/isolinux/" 2>&1 | head -5
echo "--- espacio ---"
df -h / /mnt/build

echo ""
echo "=== LISTO ==="
echo "OJO: estos bind mounts NO sobreviven un reinicio de la VM."
echo "Si reinicias antes de terminar el build, hay que volver a correr"
echo "los 3 'sudo mount --bind ...' de este script antes de compilar."
