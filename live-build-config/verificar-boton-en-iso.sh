#!/bin/bash
# verificar-boton-en-iso.sh - Confirma si "Buscar Actualizaciones"
# (el boton, dentro de pawos-refugio-gui) esta realmente en el chroot
# y en el ISO mas reciente, no solo el script pawos-actualizar-gui.
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== en el chroot (usr/local/bin/pawos-refugio-gui) ==="
sudo grep -c "Buscar Actualizaciones" chroot/usr/local/bin/pawos-refugio-gui 2>&1

echo ""
echo "=== en includes.chroot_after_packages ==="
grep -c "Buscar Actualizaciones" includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui 2>&1

echo ""
echo "=== en el binario local del repo ==="
grep -c "Buscar Actualizaciones" ~/S.O.-1-ProyectoFinal-PawOS/pawos-refugio-gui 2>&1

echo ""
echo "=== dentro del ISO mismo (squashfs) ==="
sudo umount /tmp/verif_iso 2>/dev/null || true
sudo rm -rf /tmp/squashfs-root2 /tmp/verif_iso
mkdir -p /tmp/verif_iso
sudo mount -o loop live-image-amd64.hybrid.iso /tmp/verif_iso
sudo unsquashfs -d /tmp/squashfs-root2 /tmp/verif_iso/live/filesystem.squashfs usr/local/bin/pawos-refugio-gui >/dev/null 2>&1
grep -c "Buscar Actualizaciones" /tmp/squashfs-root2/usr/local/bin/pawos-refugio-gui 2>&1
sudo umount /tmp/verif_iso

echo "=== LISTO (1 = esta el boton, 0 = falta) ==="
