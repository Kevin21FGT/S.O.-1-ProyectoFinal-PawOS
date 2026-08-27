#!/bin/bash
# lanzar-build-gnome.sh - Re-corre lb config (por si "lb clean" reseteo
# el marcador de etapa) y lanza el build final de la ISO GNOME de PawOS,
# mostrando el resumen al terminar. Correr desde
# ~/S.O.-1-ProyectoFinal-PawOS/live-build-config
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== lb config (necesario si hubo un lb clean antes) ==="
lb config \
  --distribution trixie \
  --archive-areas "main contrib non-free non-free-firmware" \
  --binary-images iso-hybrid \
  --debian-installer none

echo ""
echo "=== verificando que package-lists/hooks/includes sigan intactos ==="
diff -rq includes.chroot_after_packages config/includes.chroot_after_packages && echo "includes.chroot_after_packages OK"
diff -rq package-lists config/package-lists && echo "package-lists OK"
diff -rq hooks/normal config/hooks/normal && echo "hooks OK"

echo ""
echo "=== lanzando build (esto va a tardar) ==="
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

echo ""
echo "=== LISTO ==="
