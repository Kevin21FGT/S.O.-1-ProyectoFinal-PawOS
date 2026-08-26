#!/bin/bash
# verificar-branding.sh - Verifica que el wallpaper, los avatares y el
# fondo de login quedaron dentro del ISO, y lo copia con nombre nuevo.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== montando el ISO para inspeccionar ==="
sudo mkdir -p /tmp/verif_iso
sudo umount /tmp/verif_iso 2>/dev/null || true
sudo mount -o loop live-image-amd64.hybrid.iso /tmp/verif_iso

sudo rm -rf /tmp/squashfs-root
sudo unsquashfs -d /tmp/squashfs-root /tmp/verif_iso/live/filesystem.squashfs \
  usr/share/backgrounds/pawos-wallpaper.png \
  usr/share/backgrounds/pawos-fondo-login.png \
  var/lib/AccountsService/icons/admin_refugio \
  var/lib/AccountsService/users/admin_refugio \
  etc/dconf/db/gdm.d/01-pawos-login-background \
  etc/dconf/profile/gdm \
  etc/dconf/db/local \
  >/dev/null

echo ""
echo "=== 1) wallpaper presente ==="
test -f /tmp/squashfs-root/usr/share/backgrounds/pawos-wallpaper.png && echo "presente" || echo "FALTA"

echo ""
echo "=== 2) fondo de login presente ==="
test -f /tmp/squashfs-root/usr/share/backgrounds/pawos-fondo-login.png && echo "presente" || echo "FALTA"

echo ""
echo "=== 3) avatar de admin_refugio presente ==="
test -f /tmp/squashfs-root/var/lib/AccountsService/icons/admin_refugio && echo "presente" || echo "FALTA"
cat /tmp/squashfs-root/var/lib/AccountsService/users/admin_refugio 2>/dev/null || echo "FALTA archivo de usuario"

echo ""
echo "=== 4) dconf de gdm presente ==="
test -f /tmp/squashfs-root/etc/dconf/db/gdm.d/01-pawos-login-background && echo "presente" || echo "FALTA"
cat /tmp/squashfs-root/etc/dconf/profile/gdm 2>/dev/null || echo "FALTA perfil gdm"

echo ""
echo "=== 5) dconf ya compilado (binario, prueba de que dconf update SI corrio) ==="
test -f /tmp/squashfs-root/etc/dconf/db/local && echo "compilado (bien)" || echo "FALTA -- dconf update no corrio"

sudo umount /tmp/verif_iso

echo ""
echo "=== copiando a la carpeta compartida con nombre nuevo ==="
NOMBRE="PawOS-$(date +%Y%m%d-%H%M).iso"
cp live-image-amd64.hybrid.iso /media/sf_compartido/"$NOMBRE"
ls -la /media/sf_compartido/"$NOMBRE"
md5sum /media/sf_compartido/"$NOMBRE"

echo ""
echo "=== copiado como: $NOMBRE ==="
