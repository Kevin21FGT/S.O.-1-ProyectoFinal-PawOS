#!/bin/bash
# verificar-novedades.sh - Confirma si la version de pawos-actualizar-gui
# instalada en cada lugar ya tiene el bloque de "novedades" o es la
# version vieja (sin eso).
echo "=== en el repo (fuente) ==="
grep -c "Novedades de esta actualizacion" ~/S.O.-1-ProyectoFinal-PawOS/pawos-actualizar-gui 2>&1

echo "=== instalado en el sistema (/usr/local/bin) ==="
grep -c "Novedades de esta actualizacion" /usr/local/bin/pawos-actualizar-gui 2>&1

echo "=== dentro de includes.chroot_after_packages (para la ISO) ==="
grep -c "Novedades de esta actualizacion" ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui 2>&1

echo "=== dentro del chroot ya construido ==="
sudo grep -c "Novedades de esta actualizacion" ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/chroot/usr/local/bin/pawos-actualizar-gui 2>&1

echo "=== dentro del ISO mismo (extraido del squashfs, el contenido real que arranca) ==="
cd /tmp
rm -rf verif_squash squashfs-root
mkdir -p verif_iso
sudo mount -o loop ~/S.O.-1-ProyectoFinal-PawOS/live-build-config/live-image-amd64.hybrid.iso verif_iso
sudo unsquashfs -d /tmp/squashfs-root verif_iso/live/filesystem.squashfs usr/local/bin/pawos-actualizar-gui >/dev/null 2>&1
grep -c "Novedades de esta actualizacion" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui 2>&1
sudo umount verif_iso

echo "=== LISTO (si todos dicen 1, esta bien; si algun 0, falta ese lugar) ==="
