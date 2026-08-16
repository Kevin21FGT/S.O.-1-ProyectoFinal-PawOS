#!/bin/bash
# diagnostico-particion.sh - Revisa como esta particionado el disco
# antes de agrandarlo, para saber que tipo de tabla de particiones
# tiene (MBR o GPT) y si hay LVM de por medio.

echo "=== lsblk ==="
lsblk

echo ""
echo "=== tabla de particiones de /dev/sda ==="
sudo fdisk -l /dev/sda

echo ""
echo "=== tipo de sistema de archivos en sda1 ==="
sudo blkid /dev/sda1

echo ""
echo "=== LVM? (si no muestra nada, no hay LVM) ==="
sudo pvs 2>/dev/null
sudo lvs 2>/dev/null

echo "=== LISTO ==="
