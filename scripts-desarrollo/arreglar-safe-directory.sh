#!/bin/bash
# arreglar-safe-directory.sh - Agrega "git config --global --add
# safe.directory" dentro de pawos-actualizar-gui para que cualquier
# usuario (admin/veterinario/voluntario) pueda usar /opt/pawos-src sin
# el error de "posesion dudosa" de git, sin tener que correr el comando
# a mano. Corre desde ~/S.O.-1-ProyectoFinal-PawOS
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS

if grep -q "safe.directory" pawos-actualizar-gui; then
  echo "Ya estaba aplicado, no se toca nada."
else
  sed -i '/^REPO_DIR="\/opt\/pawos-src"$/a\
\
# Evita el error de git "posesion dudosa" ya que la carpeta la crea\
# root pero la usan distintos usuarios (admin/veterinario/voluntario).\
git config --global --add safe.directory "$REPO_DIR" 2>/dev/null || true' pawos-actualizar-gui
  echo "Linea agregada."
fi

echo ""
echo "=== verificando ==="
grep -A3 "safe.directory" pawos-actualizar-gui

echo ""
echo "=== copiando a los 3 lugares del ISO ==="
cp pawos-actualizar-gui live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui
cp pawos-actualizar-gui live-build-config/chroot/usr/local/bin/pawos-actualizar-gui
sudo chmod 755 live-build-config/chroot/usr/local/bin/pawos-actualizar-gui

echo ""
echo "=== commit + push (solo el archivo fuente, no config/) ==="
git add pawos-actualizar-gui live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui
git commit -m "Arregla error de git safe.directory en el actualizador"
git push origin rama-Kevin

echo ""
echo "=== rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
