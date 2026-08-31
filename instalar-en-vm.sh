#!/bin/bash
# instalar-en-vm.sh
#
# Compila el GUI desde el repo y lo instala en /usr/local/bin, que es
# de donde lee el icono del escritorio "PawOS Refugio (GUI)". Sin
# este paso, el icono se queda pegado en la ultima version instalada
# aunque ya hayas compilado cambios nuevos en la carpeta del repo.
#
# Uso: parado en la raiz del repo:
#     bash instalar-en-vm.sh
#
# Te va a pedir tu contrasena de sudo para copiar el binario a
# /usr/local/bin.

set -e

echo "==> Compilando GUI..."
make clean-gui
make gui

echo ""
echo "==> Instalando en /usr/local/bin (pide contrasena de sudo)..."
sudo cp pawos-refugio-gui /usr/local/bin/pawos-refugio-gui

echo ""
echo "==========================================================="
echo " Listo. El icono 'PawOS Refugio (GUI)' del escritorio ya usa"
echo " la version recien compilada. Cierra la ventana de PawOS si"
echo " la tenias abierta y vuelve a abrirla."
echo "==========================================================="
