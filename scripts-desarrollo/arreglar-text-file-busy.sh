#!/bin/bash
# arreglar-text-file-busy.sh - Arregla el error "Text file busy": el
# actualizador no puede sobrescribir su propio binario mientras esta
# corriendo. Se arregla copiando con otro nombre y luego renombrando
# encima (mv si es atomico y funciona con el binario en uso).
set -e

cd ~/S.O.-1-ProyectoFinal-PawOS

echo "=== 1) actualizando el paso de instalacion en pawos-actualizar-gui ==="
python3 - <<'PYEOF'
import re

with open("pawos-actualizar-gui") as f:
    contenido = f.read()

viejo = '''if ! sudo /usr/bin/cp "$REPO_DIR/pawos-refugio-gui" /usr/local/bin/pawos-refugio-gui || \\
   ! sudo /usr/bin/cp "$REPO_DIR/pawos-refugio" /usr/local/bin/pawos-refugio; then
  echo ""
  echo "ERROR: no se pudo instalar la actualizacion (permisos)."
  read -p "Presiona Enter para cerrar..."
  exit 1
fi
sudo /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui /usr/local/bin/pawos-refugio'''

nuevo = '''# Se copia con otro nombre y se renombra encima (mv), en vez de
# sobrescribir directo, porque el binario puede estar corriendo en
# este momento (el usuario abrio el actualizador desde la propia app)
# y sobrescribirlo directo da "Text file busy".
if ! sudo /usr/bin/cp "$REPO_DIR/pawos-refugio-gui" /usr/local/bin/pawos-refugio-gui.new || \\
   ! sudo /usr/bin/cp "$REPO_DIR/pawos-refugio" /usr/local/bin/pawos-refugio.new; then
  echo ""
  echo "ERROR: no se pudo instalar la actualizacion (permisos)."
  read -p "Presiona Enter para cerrar..."
  exit 1
fi
sudo /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new
if ! sudo /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui || \\
   ! sudo /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio; then
  echo ""
  echo "ERROR: no se pudo instalar la actualizacion (permisos)."
  read -p "Presiona Enter para cerrar..."
  exit 1
fi'''

if viejo not in contenido:
    print("NO SE ENCONTRO EL BLOQUE VIEJO -- abortando sin tocar nada")
    raise SystemExit(1)

contenido = contenido.replace(viejo, nuevo)
with open("pawos-actualizar-gui", "w") as f:
    f.write(contenido)
print("Script actualizado.")
PYEOF

echo ""
echo "=== 2) actualizando sudoers para permitir el nuevo flujo (cp .new + mv) ==="
cat > /tmp/pawos-actualizar-nuevo << 'SUDOEOF'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
SUDOEOF

sudo cp /tmp/pawos-actualizar-nuevo live-build-config/chroot/etc/sudoers.d/pawos-actualizar
sudo chmod 440 live-build-config/chroot/etc/sudoers.d/pawos-actualizar
sudo chown root:root live-build-config/chroot/etc/sudoers.d/pawos-actualizar

# tambien actualizamos el hook (para que quede permanente en futuros rebuilds completos)
sudo python3 - << 'PYEOF2'
import re

nueva_linea = "%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio\n"

rutas = [
    "live-build-config/hooks/normal/0130-configurar-actualizador.hook.chroot",
    "live-build-config/config/hooks/normal/0130-configurar-actualizador.hook.chroot",
]

for ruta in rutas:
    with open(ruta) as f:
        lineas = f.readlines()
    lineas_nuevas = []
    reemplazado = False
    for linea in lineas:
        if linea.startswith("%pawos-refugio ALL="):
            lineas_nuevas.append(nueva_linea)
            reemplazado = True
        else:
            lineas_nuevas.append(linea)
    with open(ruta, "w") as f:
        f.writelines(lineas_nuevas)
    print(f"{ruta}: {'actualizado' if reemplazado else 'NO SE ENCONTRO LA LINEA VIEJA'}")
PYEOF2

echo ""
echo "=== 3) copiando el script actualizado a los 3 lugares del ISO ==="
sudo cp pawos-actualizar-gui live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui
sudo cp pawos-actualizar-gui live-build-config/chroot/usr/local/bin/pawos-actualizar-gui
sudo chmod 755 live-build-config/chroot/usr/local/bin/pawos-actualizar-gui

echo ""
echo "=== 4) commit + push (solo lo de la carpeta fuente, no config/) ==="
git add pawos-actualizar-gui live-build-config/includes.chroot_after_packages/usr/local/bin/pawos-actualizar-gui live-build-config/hooks/normal/0130-configurar-actualizador.hook.chroot
git commit -m "Arregla error 'Text file busy' al autoactualizarse (cp+mv en vez de cp directo)"
git push origin rama-Kevin

echo ""
echo "=== 5) rebuild rapido ==="
cd live-build-config
sudo lb clean --binary

echo ""
echo "=== LISTO: ahora corre ./lanzar-build-gnome.sh ==="
