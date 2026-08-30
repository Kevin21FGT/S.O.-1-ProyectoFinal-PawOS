#!/bin/bash
# arreglar-actualizador-completo.sh - Aplica el arreglo del
# actualizador (ruta fija /opt/pawos-src + sudoers) al chroot ya
# construido, al hook para futuros builds, actualiza el script en
# todos lados, hace commit+push, y reconstruye el ISO.
set -e

REPO=~/S.O.-1-ProyectoFinal-PawOS
LBCFG="$REPO/live-build-config"

echo "=== 1) copiando el hook nuevo a ambas copias ==="
cp /media/sf_compartido/0130-configurar-actualizador.hook.chroot "$LBCFG/hooks/normal/"
cp /media/sf_compartido/0130-configurar-actualizador.hook.chroot "$LBCFG/config/hooks/normal/"
chmod 755 "$LBCFG/hooks/normal/0130-configurar-actualizador.hook.chroot"
chmod 755 "$LBCFG/config/hooks/normal/0130-configurar-actualizador.hook.chroot"

echo ""
echo "=== 2) aplicando el mismo arreglo directo al chroot ya construido ==="
sudo mkdir -p "$LBCFG/chroot/opt/pawos-src"
sudo chroot "$LBCFG/chroot" chown root:pawos-refugio /opt/pawos-src
sudo chroot "$LBCFG/chroot" chmod 2775 /opt/pawos-src
sudo tee "$LBCFG/chroot/etc/sudoers.d/pawos-actualizar" > /dev/null << 'EOF'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui /usr/local/bin/pawos-refugio
EOF
sudo chmod 440 "$LBCFG/chroot/etc/sudoers.d/pawos-actualizar"

echo ""
echo "=== 3) actualizando pawos-actualizar-gui en todos lados ==="
cp /media/sf_compartido/pawos-actualizar-gui "$REPO/pawos-actualizar-gui"
chmod 755 "$REPO/pawos-actualizar-gui"
sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"
sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"
sudo cp "$REPO/pawos-actualizar-gui" /usr/local/bin/pawos-actualizar-gui
sudo chmod 755 /usr/local/bin/pawos-actualizar-gui

echo ""
echo "=== 4) commit + push ==="
cd "$REPO"
git add -A
git commit -m "Arregla el boton de actualizar: usa ruta fija /opt/pawos-src (en vez de \$HOME) para que las reglas de sudoers funcionen sin importar el usuario, y agrega el permiso NOPASSWD necesario para instalar el binario."
git push origin rama-Kevin

echo ""
echo "=== 5) reconstruyendo el ISO (solo etapa binaria) ==="
cd "$LBCFG"
sudo lb clean --binary
./lanzar-build-gnome.sh

echo ""
echo "=== 6) copiando a la carpeta compartida ==="
cp live-image-amd64.hybrid.iso /media/sf_compartido/

echo "=== LISTO ==="
