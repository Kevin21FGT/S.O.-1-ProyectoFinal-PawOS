#!/bin/bash
# aplicar-gnome.sh - Aplica el cambio de Openbox a GNOME completo en la
# configuracion de la ISO de PawOS (live-build-config). Correr desde
# ~/S.O.-1-ProyectoFinal-PawOS/live-build-config, como usuario normal
# (no root, no hace falta sudo para esto).
set -e

echo "=== 1) Paquetes: quitar lightdm (choca con gdm3), agregar GNOME completo ==="
for f in package-lists/pawos.list.chroot config/package-lists/pawos.list.chroot; do
  grep -v -E "^(lightdm|lightdm-gtk-greeter)$" "$f" > /tmp/pl.tmp
  printf 'task-gnome-desktop\ngdm3\nnetwork-manager\nnetwork-manager-applet\ngnome-shell-extension-desktop-icons-ng\n' >> /tmp/pl.tmp
  awk '!seen[$0]++' /tmp/pl.tmp > "$f"
done
diff package-lists/pawos.list.chroot config/package-lists/pawos.list.chroot && echo "package-lists IGUALES"
echo "--- contenido final ---"
cat package-lists/pawos.list.chroot

echo "=== 2) Imagenes de branding ==="
mkdir -p includes.chroot_after_packages/usr/share/backgrounds includes.chroot_after_packages/usr/share/icons
cp ~/S.O.-1-ProyectoFinal-PawOS/branding/pawos-wallpaper.png includes.chroot_after_packages/usr/share/backgrounds/pawos-wallpaper.png
cp ~/S.O.-1-ProyectoFinal-PawOS/branding/pawos-icon.png includes.chroot_after_packages/usr/share/icons/pawos-icon.png

echo "=== 3) dconf: fondo de pantalla por defecto para todos los usuarios ==="
mkdir -p includes.chroot_after_packages/etc/dconf/profile
cat > includes.chroot_after_packages/etc/dconf/profile/user << 'EOF'
user-db:user
system-db:local
EOF
mkdir -p includes.chroot_after_packages/etc/dconf/db/local.d
cat > includes.chroot_after_packages/etc/dconf/db/local.d/00-pawos-background << 'EOF'
[org/gnome/desktop/background]
picture-uri='file:///usr/share/backgrounds/pawos-wallpaper.png'
picture-uri-dark='file:///usr/share/backgrounds/pawos-wallpaper.png'
picture-options='zoom'

[org/gnome/desktop/screensaver]
picture-uri='file:///usr/share/backgrounds/pawos-wallpaper.png'
EOF

echo "=== 4) gdm3: autologin (reemplaza lo que hacia lightdm) ==="
mkdir -p includes.chroot_after_packages/etc/gdm3
cat > includes.chroot_after_packages/etc/gdm3/custom.conf << 'EOF'
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=admin_refugio

[security]

[xdmcp]

[chooser]

[debug]
EOF

echo "=== 5) Autoarranque del CLI en cada login GNOME ==="
mkdir -p includes.chroot_after_packages/etc/skel/.config/autostart
cat > includes.chroot_after_packages/etc/skel/.config/autostart/pawos-refugio-cli.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio (auto)
Exec=xterm -fullscreen -e /usr/local/bin/pawos-refugio
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF

echo "=== 6) Sincronizando includes.chroot_after_packages con config/ ==="
cp -r includes.chroot_after_packages/* config/includes.chroot_after_packages/
diff -rq includes.chroot_after_packages config/includes.chroot_after_packages && echo "includes.chroot_after_packages IGUALES"

echo "=== Verificacion final ==="
ls -la includes.chroot_after_packages/usr/share/backgrounds/ includes.chroot_after_packages/etc/dconf/db/local.d/ includes.chroot_after_packages/etc/gdm3/
bash -n includes.chroot_after_packages/etc/skel/.config/autostart/pawos-refugio-cli.desktop 2>/dev/null || true
echo "=== LISTO ==="
