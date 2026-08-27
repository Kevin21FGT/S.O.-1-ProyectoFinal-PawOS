#!/bin/bash
# recopiar-y-verificar.sh - Vuelve a copiar el ISO a la carpeta
# compartida y muestra tamano/hash para comparar con lo que ves en
# Windows, sin depender de la hora del reloj.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== tamano y hash del ISO en la VM ==="
ls -la live-image-amd64.hybrid.iso
md5sum live-image-amd64.hybrid.iso

echo ""
echo "=== copiando de nuevo a la carpeta compartida ==="
rm -f /media/sf_compartido/live-image-amd64.hybrid.iso
cp live-image-amd64.hybrid.iso /media/sf_compartido/
sync

echo ""
echo "=== tamano y hash en la carpeta compartida (debe ser identico) ==="
ls -la /media/sf_compartido/live-image-amd64.hybrid.iso
md5sum /media/sf_compartido/live-image-amd64.hybrid.iso

echo "=== LISTO ==="
