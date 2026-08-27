#!/bin/bash
# limpiar-y-relanzar.sh - Quita el symlink viejo chroot/binary (basura
# de un intento anterior) y relanza el build.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== quitando chroot/binary viejo ==="
sudo rm -f chroot/binary
ls -la chroot/binary 2>&1 || echo "  (confirmado: ya no existe)"

echo ""
echo "=== relanzando build ==="
sudo lb build 2>&1 | tee build.log

echo ""
echo "=== ultimas 80 lineas del log ==="
tail -80 build.log

echo ""
echo "=== errores (filtrando falsos positivos conocidos) ==="
grep -i "error\|fail" build.log | grep -v "0 to remove\|0 not upgraded\|ignored" || echo "(sin coincidencias)"

echo ""
echo "=== ISO generada ==="
ls -la live-image-amd64.hybrid.iso

echo "=== LISTO ==="
