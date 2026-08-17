#!/bin/bash
# arreglar-commit-git.sh - Termina el paso de commit que se corto porque
# config/ esta en .gitignore (a proposito, es una copia regenerada).
# Solo se sube el archivo de la carpeta fuente (package-lists/).
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS
git add live-build-config/package-lists/pawos-git.list.chroot
git commit -m "Agrega git como paquete del sistema (requerido por el actualizador)"
git push origin rama-Kevin

echo ""
echo "=== rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./anclar-pawos-refugio.sh y luego ./lanzar-build-gnome.sh ==="
