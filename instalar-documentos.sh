#!/bin/bash
# instalar-documentos.sh
#
# Instala en ESTA maquina los dos scripts que usa el Portal de Clientes
# para generar y enviar PDF, y la regla de sudo para poder enviarlos:
#   - pawos-generar-pdf-documento.py  (genera el PDF)
#   - pawos-enviar-documento          (lo manda por correo / WhatsApp)
#
# Uso (desde la carpeta donde estan los archivos):
#   cd /media/sf_PawOS-Compartido
#   sudo bash instalar-documentos.sh

set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "Corre este script con sudo:  sudo bash instalar-documentos.sh"
  exit 1
fi

AQUI="$(cd "$(dirname "$0")" && pwd)"

for f in pawos-generar-pdf-documento.py pawos-enviar-documento; do
  if [ ! -f "$AQUI/$f" ]; then
    echo "ERROR: no se encontro $f junto a este script."
    exit 1
  fi
done

install -m 755 "$AQUI/pawos-generar-pdf-documento.py" /usr/local/bin/pawos-generar-pdf-documento.py
install -m 755 "$AQUI/pawos-enviar-documento"          /usr/local/bin/pawos-enviar-documento

# Regla de sudo: cualquier colaborador del grupo pawos-refugio puede enviar
# documentos (el script solo acepta PDF, ver pawos-enviar-documento).
TMP="$(mktemp)"
echo "%pawos-refugio ALL=(ALL) NOPASSWD: /usr/local/bin/pawos-enviar-documento" > "$TMP"
if visudo -cf "$TMP" > /dev/null; then
  install -m 440 -o root -g root "$TMP" /etc/sudoers.d/pawos-documentos
  echo "Regla de sudo instalada: /etc/sudoers.d/pawos-documentos"
else
  echo "ERROR: la regla de sudo no paso la validacion (visudo). No se instalo."
  rm -f "$TMP"
  exit 1
fi
rm -f "$TMP"

# fpdf2 (generador de PDF) -- PawOS ya lo instala, esto solo lo verifica
if ! python3 -c "import fpdf" 2>/dev/null; then
  echo "Falta la libreria fpdf2, instalando..."
  pip install fpdf2 --break-system-packages
fi

# segno (genera el codigo QR del carnet; si falta, el carnet sale sin QR)
if ! python3 -c "import segno" 2>/dev/null; then
  echo "Instalando segno (codigo QR)..."
  pip install segno --break-system-packages || echo "AVISO: no se pudo instalar segno, el carnet saldra sin QR."
fi

echo ""
echo "Listo. Scripts instalados en /usr/local/bin."
echo "Si tu usuario no esta en el grupo pawos-refugio, el envio por sudo no funcionara:"
echo "  id   (debe incluir pawos-refugio)"
