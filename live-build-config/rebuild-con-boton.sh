#!/bin/bash
# rebuild-con-boton.sh - Reconstruye solo la parte binaria del ISO
# (el chroot ya tiene el boton "Buscar Actualizaciones" parchado),
# usando lb clean --binary para no rehacer la instalacion de GNOME.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== limpiando solo la etapa binaria ==="
sudo lb clean --binary

echo ""
echo "=== relanzando build ==="
./lanzar-build-gnome.sh

echo ""
echo "=== copiando a la carpeta compartida ==="
cp live-image-amd64.hybrid.iso /media/sf_compartido/

echo "=== LISTO ==="
