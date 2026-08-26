#!/bin/bash
# revisar-isolinux2.sh - Segunda ronda: ver si binary/chroot siguen
# siendo symlinks validos, si el disco nuevo sigue montado, y que
# quedo realmente en /mnt/build tras el build fallido.
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== disco nuevo montado? ==="
mount | grep sdc

echo ""
echo "=== entradas chroot/cache/binary/pawos.transfer en live-build-config ==="
ls -la | grep -E "chroot|cache|binary|transfer"

echo ""
echo "=== contenido directo de /mnt/build ==="
ls -la /mnt/build/

echo ""
echo "=== espacio en ambos discos ahora ==="
df -h / /mnt/build

echo ""
echo "=== ultimas 150 lineas del build.log (para ver el error completo con mas contexto) ==="
tail -150 build.log

echo "=== LISTO ==="
