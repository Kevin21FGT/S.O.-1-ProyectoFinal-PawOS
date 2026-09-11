#!/bin/bash
# check-observaciones.sh - Confirma si la columna "observaciones" de
# vacunas (PR #21) esta realmente en el codigo fuente que se compilo
# para el ISO, y en el binario ya compilado.
cd ~/S.O.-1-ProyectoFinal-PawOS

echo "=== commit donde se agrego 'observaciones' (si existe en el historial) ==="
git log --oneline --all --grep="observaciones" -i

echo ""
echo "=== esta 'observaciones' en el codigo fuente actual (src/)? ==="
grep -rli "observaciones" src/ 2>/dev/null

echo ""
echo "=== esta compilado dentro del binario actual de la GUI? ==="
grep -c "[Oo]bservaciones" pawos-refugio-gui 2>/dev/null && echo "  (SI aparece en el binario)" || echo "  (NO aparece en el binario)"

echo ""
echo "=== fecha de compilacion del binario actual vs fecha del ultimo commit ==="
ls -la pawos-refugio-gui 2>/dev/null
git log -1 --format="ultimo commit: %ci"

echo "=== LISTO ==="
