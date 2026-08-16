#!/bin/bash
# actualizar-gui-y-rebuild.sh - Recompila la GUI, la parcha directo en
# el chroot ya construido (para no rehacer la instalacion de GNOME),
# actualiza las copias de includes.chroot_after_packages para que
# quede en git, y relanza solo la etapa binaria del build.
set -e

REPO=~/S.O.-1-ProyectoFinal-PawOS
LBCFG="$REPO/live-build-config"

echo "=== 1) recompilando la GUI ==="
cd "$REPO"
make clean-gui && make gui

echo ""
echo "=== 2) actualizando includes.chroot_after_packages (las dos copias) ==="
sudo cp pawos-refugio-gui "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"
sudo cp pawos-refugio-gui "$LBCFG/config/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"
sudo chmod 755 "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"
sudo chmod 755 "$LBCFG/config/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"

echo ""
echo "=== 3) parchando el binario directo en el chroot ya construido ==="
sudo cp pawos-refugio-gui "$LBCFG/chroot/usr/local/bin/pawos-refugio-gui"
sudo chmod 755 "$LBCFG/chroot/usr/local/bin/pawos-refugio-gui"
ls -la "$LBCFG/chroot/usr/local/bin/pawos-refugio-gui"

echo ""
echo "=== 4) limpiando solo la etapa binaria (deja el chroot intacto) ==="
cd "$LBCFG"
sudo lb clean --binary

echo ""
echo "=== 5) relanzando build (deberia ser mucho mas rapido, sin reinstalar GNOME) ==="
./lanzar-build-gnome.sh
