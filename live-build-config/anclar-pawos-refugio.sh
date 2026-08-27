#!/bin/bash
# anclar-pawos-refugio.sh - Crea el lanzador (.desktop) de PawOS Refugio
# para que aparezca en el grid de apps / Actividades de GNOME (buscable,
# se puede anclar a favoritos con clic derecho), en vez de solo poder
# abrirse desde terminal. Corre desde
# ~/S.O.-1-ProyectoFinal-PawOS/live-build-config
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

DESKTOP_FILE_CONTENT='[Desktop Entry]
Name=PawOS Refugio
Comment=Sistema de gestion de refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
Icon=preferences-system
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true'

echo "=== 1) agregando el .desktop directo al chroot ya construido (rapido) ==="
echo "$DESKTOP_FILE_CONTENT" | sudo tee chroot/usr/share/applications/pawos-refugio-gui.desktop
sudo chmod 644 chroot/usr/share/applications/pawos-refugio-gui.desktop

echo ""
echo "=== 2) agregando tambien a includes.chroot_after_packages (para que quede permanente) ==="
sudo mkdir -p includes.chroot_after_packages/usr/share/applications
echo "$DESKTOP_FILE_CONTENT" | sudo tee includes.chroot_after_packages/usr/share/applications/pawos-refugio-gui.desktop
sudo chmod 644 includes.chroot_after_packages/usr/share/applications/pawos-refugio-gui.desktop
sudo mkdir -p config/includes.chroot_after_packages/usr/share/applications
echo "$DESKTOP_FILE_CONTENT" | sudo tee config/includes.chroot_after_packages/usr/share/applications/pawos-refugio-gui.desktop
sudo chmod 644 config/includes.chroot_after_packages/usr/share/applications/pawos-refugio-gui.desktop

echo ""
echo "=== 3) commit + push ==="
cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/includes.chroot_after_packages/usr/share/applications/pawos-refugio-gui.desktop
git commit -m "Agrega lanzador .desktop de PawOS Refugio (aparece en Actividades)"
git push origin rama-Kevin

echo ""
echo "=== LISTO: ya se puede buscar 'PawOS Refugio' en Actividades ==="
echo "(para anclarlo al dock: clic derecho sobre el icono -> Agregar a favoritos)"
