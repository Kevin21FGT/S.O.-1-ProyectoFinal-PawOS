#!/bin/bash
# copiar-con-nombre-nuevo.sh - Copia el ISO a la carpeta compartida
# con un nombre NUEVO (con fecha/hora) para evitar que VirtualBox
# reutilice una version cacheada del mismo nombre de archivo.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

NOMBRE_NUEVO="PawOS-$(date +%Y%m%d-%H%M).iso"
cp live-image-amd64.hybrid.iso "/media/sf_compartido/$NOMBRE_NUEVO"
sync

echo "=== copiado como: $NOMBRE_NUEVO ==="
ls -la "/media/sf_compartido/$NOMBRE_NUEVO"
md5sum "/media/sf_compartido/$NOMBRE_NUEVO"
echo ""
echo "=== monta ESTE archivo (nombre nuevo) en VirtualBox ==="
