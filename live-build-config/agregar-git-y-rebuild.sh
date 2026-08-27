#!/bin/bash
# agregar-git-y-rebuild.sh - Agrega "git" como paquete del sistema PawOS
# (el boton "Buscar Actualizaciones" lo necesita para funcionar) y
# reconstruye rapido usando el chroot ya existente.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== 1) instalando git directo en el chroot ya construido (rapido) ==="
sudo cp /etc/resolv.conf chroot/etc/resolv.conf
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-get update
sudo chroot chroot apt-get install -y git
sudo umount chroot/dev chroot/proc chroot/sys
echo "git instalado en el chroot."

echo ""
echo "=== 2) agregando git a package-lists para que quede permanente ==="
echo "git" | sudo tee package-lists/pawos-git.list.chroot
sudo mkdir -p config/package-lists
echo "git" | sudo tee config/package-lists/pawos-git.list.chroot

echo ""
echo "=== 3) commit + push del nuevo archivo de paquetes ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-git.list.chroot live-build-config/config/package-lists/pawos-git.list.chroot
git commit -m "Agrega git como paquete del sistema (requerido por el actualizador)"
git push origin rama-Kevin

echo ""
echo "=== 4) rebuild rapido (lb clean --binary + build) ==="
cd live-build-config
sudo lb clean --binary
cd ..

echo ""
echo "=== LISTO: ahora corre lanzar-build-gnome.sh como siempre ==="
