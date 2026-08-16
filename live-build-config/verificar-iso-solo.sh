#!/bin/bash
# verificar-iso-solo.sh - Repite solo la verificacion del contenido
# real dentro del ISO (squashfs), limpiando restos de intentos
# anteriores primero.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

sudo umount /tmp/verif_iso 2>/dev/null || true
sudo rm -rf /tmp/squashfs-root /tmp/verif_iso
mkdir -p /tmp/verif_iso

sudo mount -o loop live-image-amd64.hybrid.iso /tmp/verif_iso
echo "=== contenido de /tmp/verif_iso/live/ ==="
ls -la /tmp/verif_iso/live/

sudo unsquashfs -d /tmp/squashfs-root /tmp/verif_iso/live/filesystem.squashfs usr/local/bin/pawos-actualizar-gui
echo ""
echo "=== resultado de la extraccion ==="
ls -la /tmp/squashfs-root/usr/local/bin/ 2>&1

echo ""
echo "=== tiene Novedades? (1 = si) ==="
grep -c "Novedades de esta actualizacion" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui

echo ""
echo "=== tiene github.com en texto plano? (0 = bien, esta escondido) ==="
grep -c "github.com" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui || echo 0

sudo umount /tmp/verif_iso
echo "=== LISTO ==="
