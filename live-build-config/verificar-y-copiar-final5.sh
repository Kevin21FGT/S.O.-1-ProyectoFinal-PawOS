#!/bin/bash
# verificar-y-copiar-final5.sh - Verifica que ncurses.h y nasm quedaron
# dentro del ISO (ademas de todo lo anterior), y lo copia a la carpeta
# compartida con nombre nuevo.
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
  usr/share/applications/pawos-refugio-gui.desktop \
  usr/bin/git \
  usr/bin/make \
  usr/include/sqlite3.h \
  usr/include/ncurses.h \
  usr/bin/nasm \
  >/dev/null

echo ""
echo "=== 1) boton 'Buscar Actualizaciones' en el binario ==="
grep -c "Buscar Actualizaciones" /tmp/squashfs-root/usr/local/bin/pawos-refugio-gui || echo "0 (FALTA)"

echo ""
echo "=== 2) fix de safe.directory en el script actualizador ==="
grep -c "safe.directory" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui || echo "0 (FALTA)"

echo ""
echo "=== 3) sin url/ramas visibles ==="
grep -c "github.com" /tmp/squashfs-root/usr/local/bin/pawos-actualizar-gui || echo "0 (bien, no deberia aparecer)"

echo ""
echo "=== 4) lanzador .desktop presente ==="
test -f /tmp/squashfs-root/usr/share/applications/pawos-refugio-gui.desktop && echo "presente" || echo "FALTA"

echo ""
echo "=== 5) git presente ==="
test -f /tmp/squashfs-root/usr/bin/git && echo "presente" || echo "FALTA"

echo ""
echo "=== 6) make presente ==="
test -f /tmp/squashfs-root/usr/bin/make && echo "presente" || echo "FALTA"

echo ""
echo "=== 7) sqlite3.h presente ==="
test -f /tmp/squashfs-root/usr/include/sqlite3.h && echo "presente" || echo "FALTA"

echo ""
echo "=== 8) ncurses.h presente ==="
test -f /tmp/squashfs-root/usr/include/ncurses.h && echo "presente" || echo "FALTA"

echo ""
echo "=== 9) nasm presente ==="
test -f /tmp/squashfs-root/usr/bin/nasm && echo "presente" || echo "FALTA"

sudo umount /tmp/verif_iso

echo ""
echo "=== copiando a la carpeta compartida con nombre nuevo ==="
NOMBRE="PawOS-$(date +%Y%m%d-%H%M).iso"
cp live-image-amd64.hybrid.iso /media/sf_compartido/"$NOMBRE"
ls -la /media/sf_compartido/"$NOMBRE"
md5sum /media/sf_compartido/"$NOMBRE"

echo ""
echo "=== copiado como: $NOMBRE ==="
