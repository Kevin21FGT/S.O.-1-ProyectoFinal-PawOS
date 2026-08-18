#!/bin/bash
# agregar-guest-additions-v2.sh - Agrega contrib al sources.list del
# chroot (faltaba, por eso no encontraba el paquete) e instala las
# Guest Additions de VirtualBox.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== limpiando mounts pegados (si los hay) ==="
sudo umount chroot/dev 2>/dev/null || true
sudo umount chroot/proc 2>/dev/null || true
sudo umount chroot/sys 2>/dev/null || true

echo ""
echo "=== agregando contrib/non-free/non-free-firmware al sources.list del chroot ==="
sudo sed -i -E 's/^(deb(-src)? http:\/\/[^ ]+ [a-z-]+) main$/\1 main contrib non-free non-free-firmware/' chroot/etc/apt/sources.list
cat chroot/etc/apt/sources.list

echo ""
echo "=== instalando Guest Additions ==="
sudo cp /etc/resolv.conf chroot/etc/resolv.conf
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-get update
sudo chroot chroot apt-get install -y virtualbox-guest-utils virtualbox-guest-x11
sudo umount chroot/dev chroot/proc chroot/sys
echo "Guest Additions instaladas en el chroot."

echo ""
echo "=== agregando a package-lists para que quede permanente ==="
printf "virtualbox-guest-utils\nvirtualbox-guest-x11\n" | sudo tee package-lists/pawos-vbox-guest.list.chroot
sudo mkdir -p config/package-lists
printf "virtualbox-guest-utils\nvirtualbox-guest-x11\n" | sudo tee config/package-lists/pawos-vbox-guest.list.chroot

echo ""
echo "=== commit + push (solo la carpeta fuente, no config/) ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-vbox-guest.list.chroot
git commit -m "Agrega VirtualBox Guest Additions (portapapeles y arrastrar-soltar)"
git push origin rama-Kevin

echo ""
echo "=== rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
