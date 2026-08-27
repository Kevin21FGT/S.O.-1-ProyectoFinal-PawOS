#!/bin/bash
# buscar-paquete-vbox.sh - Limpia los mounts que quedaron pegados y busca
# el nombre correcto del paquete de Guest Additions disponible en trixie.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== limpiando mounts pegados (si los hay) ==="
sudo umount chroot/dev 2>/dev/null || true
sudo umount chroot/proc 2>/dev/null || true
sudo umount chroot/sys 2>/dev/null || true

echo ""
echo "=== archivos de fuentes apt del chroot ==="
cat chroot/etc/apt/sources.list 2>/dev/null
cat chroot/etc/apt/sources.list.d/*.sources 2>/dev/null
cat chroot/etc/apt/sources.list.d/*.list 2>/dev/null

echo ""
echo "=== buscando paquetes relacionados a virtualbox/guest ==="
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-cache search virtualbox
echo "---"
sudo chroot chroot apt-cache search guest-additions
echo "---"
sudo chroot chroot apt-cache search open-vm
sudo umount chroot/dev chroot/proc chroot/sys

echo ""
echo "=== LISTO ==="
