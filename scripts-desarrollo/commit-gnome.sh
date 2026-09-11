#!/bin/bash
# commit-gnome.sh - Commit y push de todo el pivote a GNOME (package
# lists, gdm3, dconf, autostart, GUI actualizada, y los scripts de
# esta sesion) a rama-Kevin.
set -e
cd ~/S.O.-1-ProyectoFinal-PawOS

echo "=== estado antes ==="
git status --short

echo ""
echo "=== agregando todo ==="
git add -A

echo ""
echo "=== confirmando commit ==="
git commit -m "Pivote a GNOME completo en la ISO (live-build): task-gnome-desktop, gdm3 con autologin, wallpaper via dconf, autostart de la CLI, Calamares, y GUI actualizada. Agrega scripts de diagnostico/armado usados para resolver espacio en disco y compatibilidad de xorriso con bind mounts."

echo ""
echo "=== subiendo a GitHub (rama-Kevin) ==="
git push origin rama-Kevin

echo ""
echo "=== confirmando que quedo igual a GitHub ==="
git status --short
git log -1 --oneline

echo "=== LISTO ==="
