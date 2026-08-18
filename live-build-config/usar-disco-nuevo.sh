#!/bin/bash
# usar-disco-nuevo.sh - Formatea y monta el disco nuevo de 120GB (sdc)
# y redirige ahi las carpetas pesadas de live-build (chroot, cache,
# binary, pawos.transfer), dejando el resto de live-build-config
# (que si esta en git) intacto en su lugar.
# Correr desde CUALQUIER carpeta, como usuario normal (pide sudo
# cuando hace falta).
set -e

LBCFG=~/S.O.-1-ProyectoFinal-PawOS/live-build-config

echo "=== 0) confirmando que sdc esta vacio/sin usar ==="
sudo lsblk /dev/sdc
read -p "Esto va a BORRAR cualquier dato en /dev/sdc y formatearlo. Escribe SI para continuar: " confirm
if [ "$confirm" != "SI" ]; then
  echo "Cancelado."
  exit 1
fi

echo "=== 1) particionando y formateando /dev/sdc ==="
sudo parted -s /dev/sdc mklabel gpt
sudo parted -s /dev/sdc mkpart primary ext4 0% 100%
sleep 2
sudo mkfs.ext4 -F /dev/sdc1

echo "=== 2) montando en /mnt/build ==="
sudo mkdir -p /mnt/build
sudo mount /dev/sdc1 /mnt/build
sudo chown "$(whoami):$(whoami)" /mnt/build

echo "=== 3) agregando a /etc/fstab para que persista tras reiniciar ==="
UUID=$(sudo blkid -s UUID -o value /dev/sdc1)
if ! grep -q "$UUID" /etc/fstab; then
  echo "UUID=$UUID /mnt/build ext4 defaults 0 2" | sudo tee -a /etc/fstab
fi

echo "=== 4) limpiando build a medio hacer (libera espacio del disco viejo) ==="
cd "$LBCFG"
sudo lb clean || true

echo "=== 5) redirigiendo carpetas pesadas al disco nuevo ==="
for d in chroot cache binary pawos.transfer; do
  mkdir -p "/mnt/build/$d"
  if [ -L "$LBCFG/$d" ]; then
    echo "  $d ya es symlink, se deja igual"
  elif [ -d "$LBCFG/$d" ]; then
    echo "  moviendo contenido de $d al disco nuevo..."
    sudo rsync -a "$LBCFG/$d"/ "/mnt/build/$d"/
    sudo rm -rf "$LBCFG/$d"
    ln -s "/mnt/build/$d" "$LBCFG/$d"
  else
    ln -s "/mnt/build/$d" "$LBCFG/$d"
  fi
done

echo "=== 6) verificando ==="
ls -la "$LBCFG" | grep -E "chroot|cache|binary|transfer"
echo "--- espacio disco viejo (sda) ---"
df -h /
echo "--- espacio disco nuevo (sdc en /mnt/build) ---"
df -h /mnt/build

echo "=== LISTO ==="
