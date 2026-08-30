#!/bin/bash
# integrar-boton-y-commit.sh - Copia el binario/script del boton
# "Buscar Actualizaciones" a includes.chroot_after_packages (para que
# la proxima ISO ya lo traiga) y hace commit+push del cambio.
set -e

REPO=~/S.O.-1-ProyectoFinal-PawOS
LBCFG="$REPO/live-build-config"

echo "=== 1) copiando GUI actualizada y script de actualizacion al ISO ==="
sudo cp "$REPO/pawos-refugio-gui" "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"
sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-refugio-gui"
sudo chmod 755 "$LBCFG/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui"

echo ""
echo "=== 2) parchando tambien el chroot ya construido (para el proximo build rapido) ==="
sudo cp "$REPO/pawos-refugio-gui" "$LBCFG/chroot/usr/local/bin/pawos-refugio-gui"
sudo cp "$REPO/pawos-actualizar-gui" "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"
sudo chmod 755 "$LBCFG/chroot/usr/local/bin/pawos-refugio-gui"
sudo chmod 755 "$LBCFG/chroot/usr/local/bin/pawos-actualizar-gui"

echo ""
echo "=== 3) git add + commit + push ==="
cd "$REPO"
git status --short
git add -A
git commit -m "Agrega boton 'Buscar Actualizaciones' en la GUI: hace git pull + recompila + reinstala PawOS Refugio desde GitHub sin necesidad de rehacer el ISO. Incluye pawos-actualizar-gui y lo integra a la ISO."
git push origin rama-Kevin

echo ""
echo "=== 4) confirmando ==="
git log -1 --oneline
git status --short

echo "=== LISTO ==="
