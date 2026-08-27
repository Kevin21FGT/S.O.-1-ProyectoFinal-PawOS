#!/bin/bash
# verificar-y-copiar-final6.sh - Verifica que el fix de "Text file busy"
# (cp+mv) quedo dentro del ISO, y lo copia con nombre nuevo.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== montando el ISO para inspeccionar ==="
sudo mkdir -p /tmp/verif_iso
sudo umount /tmp/verif_iso 2>/dev/null || true
sudo mount -o loop live-image-amd64.hybrid.iso /tmp/verif_iso

sudo rm -rf /tmp/squashfs-root
sudo unsquashfs -d /tmp/squashfs-root /tmp/verif_iso/live/filesystem.squashfs \
  usr/local/bin/pawos-refugio-gui \
  usr/local/bin/pawos-actualizar-gui \
  etc/sudoers.d/pawos-actualizar \
  >/dev/null

echo ""
echo "=== 1) boton 'Buscar Actualizaciones' en el binario ==="
grep -c "Buscar Actualizaciones" /tmp/squashfs-root/usr/local/bin/pawos-refugio-gui || echo "0 (FALTA)"

echo ""
echo "=== 2) fix de 'Text file busy' (mv -f) en el script ==="
grep -c "mv -f" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui || echo "0 (FALTA)"

echo ""
echo "=== 3) sudoers actualizado con el nuevo flujo ==="
grep -c "\.new" /tmp/squashfs-root/etc/sudoers.d/pawos-actualizar || echo "0 (FALTA)"

echo ""
echo "=== 4) sin url/ramas visibles ==="
grep -c "github.com" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui || echo "0 (bien, no deberia aparecer)"

sudo umount /tmp/verif_iso

echo ""
echo "=== copiando a la carpeta compartida con nombre nuevo ==="
NOMBRE="PawOS-$(date +%Y%m%d-%H%M).iso"
cp live-image-amd64.hybrid.iso /media/sf_compartido/"$NOMBRE"
ls -la /media/sf_compartido/"$NOMBRE"
md5sum /media/sf_compartido/"$NOMBRE"

echo ""
echo "=== copiado como: $NOMBRE ==="
