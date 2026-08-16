#!/bin/bash
# aplicar-boton-actualizar.sh - Aplica el parche del boton "Buscar
# Actualizaciones" al codigo fuente, instala el script
# pawos-actualizar-gui, recompila, y prueba localmente. Correr desde
# ~/S.O.-1-ProyectoFinal-PawOS
set -e

echo "=== 1) aplicando el parche al codigo fuente (con backup) ==="
python3 agregar-boton-actualizar.py

echo ""
echo "=== 2) instalando pawos-actualizar-gui en el sistema ==="
sudo cp pawos-actualizar-gui /usr/local/bin/pawos-actualizar-gui
sudo chmod 755 /usr/local/bin/pawos-actualizar-gui

echo ""
echo "=== 3) recompilando la GUI ==="
make clean-gui && make gui

echo ""
echo "=== 4) verificando que el boton quedo en el binario ==="
grep -c "Buscar Actualizaciones" pawos-refugio-gui && echo "  (SI aparece en el binario)"

echo ""
echo "=== LISTO ==="
echo "Prueba la GUI ahora (sudo cp pawos-refugio-gui /usr/local/bin/ tras cerrar"
echo "cualquier instancia abierta) y confirma que aparece el boton nuevo entre"
echo "la cuadricula de modulos y 'Salir'."
