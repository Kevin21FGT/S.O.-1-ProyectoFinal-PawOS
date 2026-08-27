#!/bin/bash
# diagnostico-espacio.sh - Revisa espacio en disco y que esta ocupando
# lugar, despues de que "sudo lb build" fallo por falta de espacio.
# Correr desde ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== espacio total del disco/particion ==="
df -h /

echo ""
echo "=== tamano de la carpeta live-build-config (build actual) ==="
sudo du -sh ~/S.O.-1-ProyectoFinal-PawOS/live-build-config 2>/dev/null
echo "--- desglose ---"
sudo du -sh ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/* 2>/dev/null | sort -rh

echo ""
echo "=== ISOs viejas sueltas (openbox/calamares) que ya no hacen falta ==="
find ~/S.O.-1-ProyectoFinal-PawOS -maxdepth 3 -iname "*.iso" -exec ls -lh {} \;

echo ""
echo "=== cache de apt dentro del build (cache/packages.list y similares) ==="
sudo du -sh ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/cache 2>/dev/null

echo ""
echo "=== espacio libre en /tmp (por si el sistema usa /tmp para builds) ==="
df -h /tmp

echo "=== LISTO ==="
