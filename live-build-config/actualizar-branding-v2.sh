#!/bin/bash
# actualizar-branding-v2.sh - Reemplaza el wallpaper por la ilustracion
# nueva que mandaste, y reemplaza los avatares por unos con color
# SOLIDO + letra (mucho mas distinguibles entre si que el anillo fino
# de antes) para admin_refugio / veterinario1 / voluntario1.
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config
BR=/media/sf_compartido/branding

echo "=== 1) reemplazando el wallpaper por la ilustracion nueva ==="
sudo cp "$BR/pawos-wallpaper.png" includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png
sudo chmod 644 includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png

echo ""
echo "=== 2) reemplazando avatares (ahora con color solido + letra) ==="
declare -A AVATAR=(
  [admin_refugio]="pawos-avatar-admin.png"
  [veterinario1]="pawos-avatar-veterinario.png"
  [voluntario1]="pawos-avatar-voluntario.png"
)
for usuario in "${!AVATAR[@]}"; do
  sudo cp "$BR/${AVATAR[$usuario]}" "includes.chroot_after_packages/var/lib/AccountsService/icons/$usuario"
  sudo chmod 644 "includes.chroot_after_packages/var/lib/AccountsService/icons/$usuario"
  echo "   avatar reemplazado para: $usuario"
done

echo ""
echo "=== 3) aplicando directo al chroot ya construido (rebuild rapido) ==="
sudo cp includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png chroot/usr/share/backgrounds/pawos-wallpaper.png
for usuario in admin_refugio veterinario1 voluntario1; do
  sudo cp "includes.chroot_after_packages/var/lib/AccountsService/icons/$usuario" "chroot/var/lib/AccountsService/icons/$usuario"
done

echo ""
echo "=== 4) commit + push ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png \
  live-build-config/includes.chroot_after_packages/var/lib/AccountsService/icons
git commit -m "Reemplaza wallpaper por ilustracion final y mejora contraste de avatares por rol"
git push origin rama-Kevin

echo ""
echo "=== 5) rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
