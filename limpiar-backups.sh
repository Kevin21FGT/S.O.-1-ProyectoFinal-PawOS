#!/bin/bash
# limpiar-backups.sh
#
# Saca de git (pero NO borra de tu disco) los archivos .bak / .bak2 /
# .bak3 / etc. que los scripts de parcheo van dejando como respaldo
# antes de modificar cada archivo. Se quedan en tu carpeta local por
# si alguna vez necesitas revisarlos rapido, pero ya no se suben mas
# a GitHub ni aparecen en el historial de aqui en adelante. No los usa
# el programa ni el Makefile para nada, asi que esto no afecta la
# compilacion.
#
# (De todas formas, git ya guarda cada version anterior de cada
# archivo en su propio historial -- estos .bak son respaldo extra,
# no la unica forma de recuperar algo si algo se rompe.)
#
# Tambien agrega una regla a .gitignore para que estos archivos ya no
# se vuelvan a subir por accidente con "git add -A".
#
# Uso: parado en la raiz del repo:
#     bash limpiar-backups.sh

set -e

echo "==> Buscando archivos de backup (.bak, .bak2, .bak3, ...)..."
ARCHIVOS=$(git ls-files | grep -E '\.bak[0-9]*$' || true)

if [ -z "$ARCHIVOS" ]; then
    echo "No se encontraron archivos .bak en el repositorio. Nada que limpiar."
else
    echo "Se van a sacar de git estos archivos (se quedan en tu disco):"
    echo "$ARCHIVOS"
    echo ""
    echo "$ARCHIVOS" | xargs git rm --cached --quiet
    echo "Sacados de git (siguen en tu carpeta local)."
fi

echo ""
echo "==> Agregando regla a .gitignore..."
if ! grep -qxF '*.bak*' .gitignore 2>/dev/null; then
    echo '*.bak*' >> .gitignore
    echo "Regla '*.bak*' agregada a .gitignore."
else
    echo "La regla ya estaba en .gitignore."
fi

git add .gitignore

echo ""
echo "==========================================================="
echo " Listo. Revisa con 'git status' y luego:"
echo "   git commit -m \"Limpiar archivos .bak y agregar a gitignore\""
echo "   git push origin rama-Kevin"
echo "==========================================================="
