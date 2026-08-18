#!/bin/bash
# buscar-paquete-vbox-v2.sh - Ahora que contrib ya esta habilitado,
# busca el nombre real del paquete de Guest Additions en trixie.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

# por si los mounts quedaron pegados del intento anterior
sudo mount --bind /dev chroot/dev 2>/dev/null || true
sudo mount --bind /proc chroot/proc 2>/dev/null || true
sudo mount --bind /sys chroot/sys 2>/dev/null || true

echo "=== busqueda amplia 'virtualbox' ==="
sudo chroot chroot apt-cache search virtualbox || echo "(nada)"

echo ""
echo "=== busqueda amplia 'guest' ==="
sudo chroot chroot apt-cache search guest | grep -i -E "vbox|virtualbox|guest-addition" || echo "(nada)"

sudo umount chroot/dev 2>/dev/null || true
sudo umount chroot/proc 2>/dev/null || true
sudo umount chroot/sys 2>/dev/null || true

echo ""
echo "=== LISTO ==="
