#!/bin/bash
# aplicar-branding-completo.sh - Arregla el fondo de pantalla (le
# faltaba "dconf update"), agrega avatar por usuario para la pantalla
# de login de GDM, y personaliza el fondo de esa misma pantalla de
# login. Todo dentro del live-build-config actual (GNOME).
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config
BR=/media/sf_compartido/branding

echo "=== 1) reemplazando el wallpaper por el nuevo (paleta del GUI) ==="
sudo mkdir -p includes.chroot_after_packages/usr/share/backgrounds
sudo cp "$BR/pawos-wallpaper.png" includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png
sudo cp "$BR/pawos-fondo-login.png" includes.chroot_after_packages/usr/share/backgrounds/pawos-fondo-login.png
sudo chmod 644 includes.chroot_after_packages/usr/share/backgrounds/*.png

echo ""
echo "=== 2) avatares de usuario (AccountsService) ==="
sudo mkdir -p includes.chroot_after_packages/var/lib/AccountsService/icons
sudo mkdir -p includes.chroot_after_packages/var/lib/AccountsService/users

declare -A AVATAR=(
  [admin_refugio]="pawos-avatar-admin.png"
  [veterinario1]="pawos-avatar-veterinario.png"
  [voluntario1]="pawos-avatar-voluntario.png"
)
for usuario in "${!AVATAR[@]}"; do
  sudo cp "$BR/${AVATAR[$usuario]}" "includes.chroot_after_packages/var/lib/AccountsService/icons/$usuario"
  sudo chmod 644 "includes.chroot_after_packages/var/lib/AccountsService/icons/$usuario"
  cat <<EOF | sudo tee "includes.chroot_after_packages/var/lib/AccountsService/users/$usuario" > /dev/null
[User]
Icon=/var/lib/AccountsService/icons/$usuario
SystemAccount=false
EOF
  sudo chmod 644 "includes.chroot_after_packages/var/lib/AccountsService/users/$usuario"
  echo "   avatar listo para: $usuario"
done

echo ""
echo "=== 3) fondo de la pantalla de login (GDM), via dconf ==="
sudo mkdir -p includes.chroot_after_packages/etc/dconf/db/gdm.d
cat <<'EOF' | sudo tee includes.chroot_after_packages/etc/dconf/db/gdm.d/01-pawos-login-background > /dev/null
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/pawos-fondo-login.png'
picture-options='zoom'
EOF
sudo chmod 644 includes.chroot_after_packages/etc/dconf/db/gdm.d/01-pawos-login-background

sudo mkdir -p includes.chroot_after_packages/etc/dconf/profile
if [ -f includes.chroot_after_packages/etc/dconf/profile/gdm ]; then
  echo "   ya existe /etc/dconf/profile/gdm, contenido actual:"
  cat includes.chroot_after_packages/etc/dconf/profile/gdm
  if ! grep -q "system-db:gdm" includes.chroot_after_packages/etc/dconf/profile/gdm; then
    echo "system-db:gdm" | sudo tee -a includes.chroot_after_packages/etc/dconf/profile/gdm > /dev/null
    echo "   se agrego la linea system-db:gdm"
  fi
else
  cat <<'EOF' | sudo tee includes.chroot_after_packages/etc/dconf/profile/gdm > /dev/null
user-db:user
system-db:gdm
EOF
  echo "   creado /etc/dconf/profile/gdm"
fi

echo ""
echo "=== 4) hook nuevo: dconf update (esto era lo que faltaba para que el fondo funcionara) ==="
cat <<'EOF' | sudo tee hooks/normal/0140-aplicar-dconf.hook.chroot > /dev/null
#!/bin/bash
# 0140-aplicar-dconf.hook.chroot - Compila las bases de dconf (fondo
# de escritorio, fondo de la pantalla de login GDM) para que los
# archivos de configuracion en /etc/dconf/db/*.d/ realmente tengan
# efecto. Sin este paso, esos archivos quedan ahi sin hacer nada.
set -e
dconf update
EOF
sudo chmod +x hooks/normal/0140-aplicar-dconf.hook.chroot
sudo mkdir -p config/hooks/normal
sudo cp hooks/normal/0140-aplicar-dconf.hook.chroot config/hooks/normal/0140-aplicar-dconf.hook.chroot

echo ""
echo "=== 5) aplicando todo lo mismo directo al chroot ya construido (para rebuild rapido) ==="
for archivo in \
  usr/share/backgrounds/pawos-wallpaper.png \
  usr/share/backgrounds/pawos-fondo-login.png \
  var/lib/AccountsService/icons/admin_refugio \
  var/lib/AccountsService/icons/veterinario1 \
  var/lib/AccountsService/icons/voluntario1 \
  var/lib/AccountsService/users/admin_refugio \
  var/lib/AccountsService/users/veterinario1 \
  var/lib/AccountsService/users/voluntario1 \
  etc/dconf/db/gdm.d/01-pawos-login-background \
  etc/dconf/profile/gdm
do
  sudo mkdir -p "chroot/$(dirname "$archivo")"
  sudo cp "includes.chroot_after_packages/$archivo" "chroot/$archivo"
done
sudo chroot chroot dconf update
echo "   dconf update corrido directo en el chroot."

echo ""
echo "=== 6) commit + push (solo la carpeta fuente, no config/) ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/hooks/normal/0140-aplicar-dconf.hook.chroot \
  live-build-config/includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png \
  live-build-config/includes.chroot_after_packages/usr/share/backgrounds/pawos-fondo-login.png \
  live-build-config/includes.chroot_after_packages/var/lib/AccountsService \
  live-build-config/includes.chroot_after_packages/etc/dconf
git commit -m "Arregla fondo de pantalla (dconf update), agrega avatares de usuario y fondo de login GDM"
git push origin rama-Kevin

echo ""
echo "=== 7) rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
