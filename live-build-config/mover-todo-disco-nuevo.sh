#!/bin/bash
# mover-todo-disco-nuevo.sh - Mueve TODA la carpeta live-build-config
# (no solo chroot/cache/binary por separado) al disco nuevo, y la
# monta completa como un solo bind mount. Esto evita el problema de
# "mv chroot chroot.tmp: Device or resource busy" que pasa cuando
# chroot es un punto de montaje separado.
set -e

REPO=~/S.O.-1-ProyectoFinal-PawOS
LBCFG="$REPO/live-build-config"

echo "=== 0) desmontando los bind mounts individuales actuales ==="
sudo umount "$LBCFG/chroot" 2>/dev/null || true
sudo umount "$LBCFG/binary" 2>/dev/null || true
sudo umount "$LBCFG/cache" 2>/dev/null || true

echo "=== 1) copiando el resto de live-build-config (hooks, package-lists, config, etc) ==="
sudo mkdir -p /mnt/build/live-build-config
sudo rsync -a --exclude=chroot --exclude=binary --exclude=cache "$LBCFG"/ /mnt/build/live-build-config/

echo "=== 2) moviendo el contenido real de chroot/binary/cache a su lugar definitivo ==="
sudo mkdir -p /mnt/build/live-build-config/chroot /mnt/build/live-build-config/binary /mnt/build/live-build-config/cache
sudo rsync -a --remove-source-files /mnt/build/chroot/ /mnt/build/live-build-config/chroot/
sudo rsync -a --remove-source-files /mnt/build/binary/ /mnt/build/live-build-config/binary/
sudo rsync -a --remove-source-files /mnt/build/cache/ /mnt/build/live-build-config/cache/

echo "=== 3) reemplazando la carpeta original por UN bind mount completo ==="
sudo rm -rf "$LBCFG"
mkdir -p "$LBCFG"
sudo mount --bind /mnt/build/live-build-config "$LBCFG"

echo ""
echo "=== 4) verificando ==="
mount | grep "live-build-config"
echo "--- contenido de live-build-config ---"
ls "$LBCFG"
echo "--- isolinux dentro de binary ---"
ls "$LBCFG/binary/isolinux/" 2>&1 | head -5
echo "--- espacio ---"
df -h / /mnt/build

echo ""
echo "=== LISTO ==="
echo "OJO: este bind mount NO sobrevive un reinicio de la VM."
echo "Si reinicias antes de terminar, corre:"
echo "  sudo mount --bind /mnt/build/live-build-config $LBCFG"
