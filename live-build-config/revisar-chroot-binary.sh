#!/bin/bash
# revisar-chroot-binary.sh - Investiga que es "chroot/binary" (choca
# con la etapa binary_iso: "cannot overwrite non-directory
# 'chroot/binary' with directory 'binary'").
cd ~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== que es chroot/binary? ==="
sudo file chroot/binary 2>&1
sudo ls -la chroot/binary 2>&1

echo ""
echo "=== y chroot/binary.sh? (tambien parecia raro) ==="
sudo file chroot/binary.sh 2>&1
sudo ls -la chroot/binary.sh 2>&1

echo ""
echo "=== raiz completa del chroot, por si hay mas cosas raras ==="
sudo ls -la chroot/ | head -40

echo "=== LISTO ==="
