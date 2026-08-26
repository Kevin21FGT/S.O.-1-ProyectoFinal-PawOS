#!/bin/bash
# revisar-isolinux.sh - Investiga por que falta isolinux.bin en el ISO.
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== contenido de binary/isolinux/ (si existe) ==="
ls -la binary/isolinux/ 2>&1

echo ""
echo "=== contenido completo de binary/ ==="
ls -la binary/ 2>&1

echo ""
echo "=== log completo de la etapa binary_syslinux (lineas 8281-8320) ==="
sed -n '8281,8320p' build.log

echo ""
echo "=== buscando isolinux.bin en el chroot (por si se necesita copiar de ahi) ==="
find /mnt/build/chroot -iname "isolinux.bin" 2>&1

echo "=== LISTO ==="
