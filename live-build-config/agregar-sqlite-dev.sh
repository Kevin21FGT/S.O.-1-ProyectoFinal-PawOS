#!/bin/bash
# agregar-sqlite-dev.sh - Agrega libsqlite3-dev, que faltaba para
# compilar (src/db.c usa sqlite3.h).
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== limpiando mounts pegados (si los hay) ==="
sudo umount chroot/dev 2>/dev/null || true
sudo umount chroot/proc 2>/dev/null || true
sudo umount chroot/sys 2>/dev/null || true

echo ""
echo "=== instalando libsqlite3-dev en el chroot ==="
sudo cp /etc/resolv.conf chroot/etc/resolv.conf
sudo mount --bind /dev chroot/dev
sudo mount --bind /proc chroot/proc
sudo mount --bind /sys chroot/sys
sudo chroot chroot apt-get update
sudo chroot chroot apt-get install -y libsqlite3-dev
sudo umount chroot/dev chroot/proc chroot/sys
echo "libsqlite3-dev instalado."

echo ""
echo "=== agregando a package-lists para que quede permanente ==="
echo "libsqlite3-dev" | sudo tee -a package-lists/pawos-build-tools.list.chroot
sudo mkdir -p config/package-lists
echo "libsqlite3-dev" | sudo tee -a config/package-lists/pawos-build-tools.list.chroot

echo ""
echo "=== commit + push (solo la carpeta fuente, no config/) ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-build-tools.list.chroot
git commit -m "Agrega libsqlite3-dev (requerido para compilar db.c)"
git push origin rama-Kevin

echo ""
echo "=== rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
