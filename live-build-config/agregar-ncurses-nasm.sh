#!/bin/bash
# agregar-ncurses-nasm.sh - Agrega libncurses-dev y nasm, que faltaban
# para compilar el CLI (src/main.c usa ncurses.h, src/checksum.asm
# necesita nasm).
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== limpiando mounts pegados (si los hay) ==="
sudo umount chroot/dev 2>/dev/null || true
sudo umount chroot/proc 2>/dev/null || true
sudo umount chroot/sys 2>/dev/null || true

echo ""
echo "=== instalando libncurses-dev y nasm en el chroot ==="
sudo cp /etc/resolv.conf chroot/etc/resolv.conf
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-get update
sudo chroot chroot apt-get install -y libncurses-dev nasm
sudo umount chroot/dev chroot/proc chroot/sys
echo "libncurses-dev y nasm instalados."

echo ""
echo "=== agregando a package-lists para que quede permanente ==="
printf "libncurses-dev\nnasm\n" | sudo tee -a package-lists/pawos-build-tools.list.chroot
sudo mkdir -p config/package-lists
printf "libncurses-dev\nnasm\n" | sudo tee -a config/package-lists/pawos-build-tools.list.chroot

echo ""
echo "=== commit + push (solo la carpeta fuente, no config/) ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-build-tools.list.chroot
git commit -m "Agrega libncurses-dev y nasm (requeridos para compilar el CLI)"
git push origin rama-Kevin

echo ""
echo "=== rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
