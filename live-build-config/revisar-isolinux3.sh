#!/bin/bash
# revisar-isolinux3.sh - Revisa el contenido real de binary/ en el
# disco nuevo, y confirma si "chroot" sigue siendo symlink o se
# convirtio en carpeta real (lo que explicaria que sda se llenara
# de nuevo).
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== es 'chroot' symlink o carpeta real? ==="
stat chroot | head -3

echo ""
echo "=== contenido de /mnt/build/binary (recursivo, solo nombres) ==="
find /mnt/build/binary -maxdepth 2

echo ""
echo "=== buscando isolinux.bin en TODO /mnt/build ==="
find /mnt/build -iname "isolinux.bin" 2>&1

echo ""
echo "=== buscando isolinux.bin en el chroot real (local, no symlink) ==="
sudo find ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/chroot -iname "isolinux.bin" 2>&1

echo "=== LISTO ==="
