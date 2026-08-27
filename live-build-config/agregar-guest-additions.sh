#!/bin/bash
# agregar-guest-additions.sh - Agrega las Guest Additions de VirtualBox
# (portapapeles compartido, arrastrar y soltar, resolucion automatica)
# como paquetes permanentes del sistema PawOS. Corre desde
# ~/S.O.-1-ProyectoFinal-PawOS/live-build-config
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== 1) instalando directo en el chroot ya construido (rapido) ==="
sudo cp /etc/resolv.conf chroot/etc/resolv.conf
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-get update
sudo chroot chroot apt-get install -y virtualbox-guest-utils virtualbox-guest-x11
sudo umount chroot/dev chroot/proc chroot/sys
echo "Guest Additions instaladas en el chroot."

echo ""
echo "=== 2) agregando a package-lists para que quede permanente ==="
printf "virtualbox-guest-utils\nvirtualbox-guest-x11\n" | sudo tee package-lists/pawos-vbox-guest.list.chroot
sudo mkdir -p config/package-lists
printf "virtualbox-guest-utils\nvirtualbox-guest-x11\n" | sudo tee config/package-lists/pawos-vbox-guest.list.chroot

echo ""
echo "=== 3) commit + push (solo la carpeta fuente, no config/) ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-vbox-guest.list.chroot
git commit -m "Agrega VirtualBox Guest Additions (portapapeles y arrastrar-soltar)"
git push origin rama-Kevin

echo ""
echo "=== 4) rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
echo "NOTA: si el portapapeles no funciona en el escritorio, revisa que"
echo "la sesion sea 'GNOME on Xorg' (no Wayland) al iniciar sesion en GDM"
echo "-- las Guest Additions de VirtualBox necesitan X11 para el portapapeles."
