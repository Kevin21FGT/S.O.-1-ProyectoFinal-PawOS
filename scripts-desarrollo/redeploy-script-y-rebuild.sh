#!/bin/bash
# redeploy-script-y-rebuild.sh - Reemplaza pawos-actualizar-gui (ahora
# con salida generica, sin URLs ni nombres de rama) en todos los
# lugares donde vive, y reconstruye el ISO (solo etapa binaria).
set -e

REPO=~/S.O.-1-ProyectoFinal-PawOS
LBCFG="$REPO/live-build-config"

echo "=== 1) actualizando el script en el repo, el ISO y el chroot ==="
cp /media/sf_compartido/pawos-actualizar-gui "$REPO/pawos-actualizar-gui"
chmod 755 "$REPO/pawos-actualizar-gui"

sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"
sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"

echo "=== 2) probando el script localmente ==="
sudo cp "$REPO/pawos-actualizar-gui" /usr/local/bin/pawos-actualizar-gui
sudo chmod 755 /usr/local/bin/pawos-actualizar-gui

echo "=== 3) commit + push del script actualizado ==="
cd "$REPO"
git add -A
git commit -m "Limpia la salida de pawos-actualizar-gui: ya no muestra URL del repo, nombre de rama, ni comandos de git en crudo -- solo mensajes genericos como cualquier actualizador de programa."
git push origin rama-Kevin

echo ""
echo "=== 4) reconstruyendo el ISO (solo etapa binaria) ==="
cd "$LBCFG"
sudo lb clean --binary
./lanzar-build-gnome.sh

echo ""
echo "=== 5) copiando a la carpeta compartida ==="
cp live-image-amd64.hybrid.iso /media/sf_compartido/

echo "=== LISTO ==="
