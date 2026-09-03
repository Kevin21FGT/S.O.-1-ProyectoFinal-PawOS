#!/bin/bash
# actualizar-ramas-personales.sh
#
# Actualiza todas las ramas personales del equipo para que queden al
# dia con rama-Combinada, SIN pisar trabajo propio de nadie:
#
#   - Para cada rama de la lista, revisa si tiene commits propios que
#     rama-Combinada no tenga.
#   - Si NO tiene nada propio (esta "limpia"), la actualiza de forma
#     segura (git push origin origin/rama-Combinada:<rama>).
#   - Si SI tiene algo propio, la SALTA y avisa -- no se toca, para no
#     perder el trabajo de esa persona. Esa rama hay que combinarla a
#     mano (merge) despues.
#
# Uso: parado en la raiz del repo:
#   bash actualizar-ramas-personales.sh

set -e

RAMAS_PERSONALES=(
    "rama-Kevin"
    "rama-Alex"
    "rama-Jeyling"
    "rama-Osman"
    "rama-Paola"
    "rama-William"
)

echo "=== Actualizando referencias remotas ==="
git fetch origin

echo ""
echo "=== Revisando cada rama personal ==="
for rama in "${RAMAS_PERSONALES[@]}"; do
    if ! git rev-parse --verify "origin/$rama" >/dev/null 2>&1; then
        echo "  [omitida] origin/$rama no existe."
        continue
    fi

    propios=$(git log --oneline "origin/rama-Combinada..origin/$rama" | wc -l)

    if [ "$propios" -eq 0 ]; then
        echo "  [$rama] sin commits propios -> actualizando..."
        git push origin "origin/rama-Combinada:$rama"
    else
        echo "  [$rama] tiene $propios commit(s) propio(s) -> SE SALTA (no se toca)."
        echo "           Revisa con: git log --oneline origin/rama-Combinada..origin/$rama"
    fi
done

echo ""
echo "Listo. Las ramas saltadas (si hay) necesitan un merge manual,"
echo "no un simple push, para no perder el trabajo de esa persona."
