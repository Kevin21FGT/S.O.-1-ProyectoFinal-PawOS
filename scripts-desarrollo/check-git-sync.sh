#!/bin/bash
# check-git-sync.sh - Revisa si el repo local (en la VM de build) esta
# desactualizado respecto a GitHub (rama-Kevin).
cd ~/S.O.-1-ProyectoFinal-PawOS

echo "=== rama actual y estado ==="
git branch --show-current
git status

echo ""
echo "=== ultimos 5 commits locales ==="
git log -5 --oneline

echo ""
echo "=== trayendo info de GitHub (sin aplicar cambios) ==="
git fetch origin

echo ""
echo "=== hay commits en GitHub que no tienes localmente? ==="
git log HEAD..origin/rama-Kevin --oneline

echo ""
echo "=== hay commits locales que no has subido? ==="
git log origin/rama-Kevin..HEAD --oneline

echo "=== LISTO ==="
