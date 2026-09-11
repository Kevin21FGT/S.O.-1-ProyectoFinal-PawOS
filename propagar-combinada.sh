#!/bin/bash
# propagar-combinada.sh
#
# Trae los cambios de rama-Combinada a todas las ramas personales del
# equipo (pull + push, una por una), para no tener que hacerlo a mano
# rama por rama cada vez que se sube algo nuevo a rama-Combinada.
#
# Es seguro correrlo varias veces: si una rama ya esta al dia, git
# simplemente dice "Already up to date" y sigue con la siguiente.
#
# Si alguna rama tiene un conflicto de verdad (poco probable, ya que
# casi siempre son fast-forward o merges limpios), el script SE
# DETIENE ahi mismo para que lo resuelvas a mano antes de seguir --
# no sigue de largo dejando el repo a medias.
#
# Uso: parado en la raiz del repo, sin cambios pendientes:
#   bash propagar-combinada.sh

set -e

RAMAS=(rama-Kevin rama-William rama-Osman rama-Jeyling rama-Paola rama-Alex)
RAMA_ORIGINAL=$(git branch --show-current)

echo "=========================================================="
echo " Propagando rama-Combinada a: ${RAMAS[*]}"
echo "=========================================================="

git fetch origin

for RAMA in "${RAMAS[@]}"; do
    echo ""
    echo "----- $RAMA -----"
    git checkout "$RAMA"
    git pull origin rama-Combinada --no-rebase
    git push origin "$RAMA"
    echo "  ok: $RAMA actualizada y subida."
done

echo ""
echo "==> Volviendo a $RAMA_ORIGINAL..."
git checkout "$RAMA_ORIGINAL"

echo ""
echo "=========================================================="
echo " Listo. Todas las ramas quedaron al dia con rama-Combinada."
echo "=========================================================="
