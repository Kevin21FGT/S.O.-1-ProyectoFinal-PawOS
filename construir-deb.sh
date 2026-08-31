#!/bin/bash
# construir-deb.sh
#
# Arma un paquete .deb de PawOS Refugio -- el instalador "de verdad"
# al estilo Windows: tus companeros hacen doble clic en el archivo
# .deb (se abre el Centro de Software de Linux) o corren un solo
# comando de apt, y queda instalado. No necesitan tener el codigo
# fuente, ni git, ni el compilador.
#
# Diferencia con instalar-pawos.sh: ese script COMPILA en la maquina
# de destino. Este en cambio se compila UNA VEZ aqui (en tu VM, que ya
# tiene todo el toolchain) y el resultado (el .deb) ya trae los
# binarios listos -- el companero no compila nada.
#
# Cambio de diseno a proposito: como el login de la app ya no depende
# de cuentas de Linux (usa la base de datos), este instalador YA NO
# crea las cuentas fijas admin_refugio/veterinario1/voluntario1 con
# contrasena en el codigo. En vez de eso, agrega automaticamente a
# quien instale el paquete (el usuario real detras de "sudo") a los
# grupos pawos-admin y pawos-refugio, que es lo que hace falta para
# que el respaldo en la nube y el acceso a la base de datos funcionen
# -- exactamente lo mismo que se dejo configurado a mano para
# vboxuser en esta VM.
#
# Uso: parado en la raiz del repo (con todo compilado o para
# compilar de una vez):
#     bash construir-deb.sh
#
# Al final queda un archivo pawos-refugio_<version>_amd64.deb en la
# carpeta actual, listo para copiar a una USB, subirlo a Drive, o
# adjuntarlo como "Release" en GitHub.

set -e

if [ ! -f "Makefile" ]; then
    echo "ERROR: corre este script desde la raiz del repo (donde esta el Makefile)."
    exit 1
fi

VERSION=$(grep -oP '(?<=PAWOS_VERSION ")[^"]+' include/version.h 2>/dev/null || echo "1.0")
PKG="pawos-refugio"
ARCH="amd64"
NOMBRE_DEB="${PKG}_${VERSION}_${ARCH}.deb"
RAIZ="deb-build/${PKG}_${VERSION}_${ARCH}"

echo "=== 1. Compilando (version detectada: $VERSION) ==="
make clean
make all
make clean-gui
make gui

echo "=== 2. Armando estructura del paquete ==="
rm -rf "deb-build"
mkdir -p "$RAIZ/DEBIAN"
mkdir -p "$RAIZ/usr/local/bin"
mkdir -p "$RAIZ/usr/share/applications"
mkdir -p "$RAIZ/usr/share/icons"
mkdir -p "$RAIZ/etc/systemd/system"
mkdir -p "$RAIZ/etc/sudoers.d"

install -m 755 pawos-refugio        "$RAIZ/usr/local/bin/pawos-refugio"
install -m 755 pawos-vacunas-check  "$RAIZ/usr/local/bin/pawos-vacunas-check"
install -m 755 pawos-monitoreo      "$RAIZ/usr/local/bin/pawos-monitoreo"
install -m 755 pawos-refugio-gui    "$RAIZ/usr/local/bin/pawos-refugio-gui"
[ -f branding/pawos-icon.png ] && install -m 644 branding/pawos-icon.png "$RAIZ/usr/share/icons/pawos-icon.png"

echo "=== 3. Control del paquete (DEBIAN/control) ==="
cat > "$RAIZ/DEBIAN/control" << EOF
Package: ${PKG}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: libgtk-3-0, libsqlite3-0, libncurses6, libcrypt1, python3, ufw, rclone
Maintainer: Kevin Fuentes <${email:-kevin@pawos.local}>
Description: PawOS Refugio - Sistema de gestion para refugios de animales
 Sistema de gestion (GUI y consola) para refugios de animales:
 mascotas, vacunas, adopciones, donantes, reportes, administracion
 de procesos, memoria y respaldo en la nube.
EOF

echo "=== 4. Accesos directos (.desktop) ==="
cat > "$RAIZ/usr/share/applications/pawos-refugio.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio
Exec=x-terminal-emulator -e /usr/local/bin/pawos-refugio
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-refugio-gui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio (GUI)
Comment=Sistema de gestion para refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-apagar.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=Apagar PawOS
Exec=sudo /sbin/poweroff
Terminal=false
Icon=system-shutdown
Categories=Utility;
EOF

echo "=== 5. Scripts de respaldo en la nube ==="
cat > "$RAIZ/usr/local/bin/pawos-backup-nube" << 'BACKUPEOF'
#!/bin/bash
set -e
REMOTE="ggdrive:PawOS_Backups"
FECHA=$(date +%Y%m%d_%H%M%S_%N); FECHA="${FECHA:0:19}"
ETIQUETA_RAW="$1"
if [ -z "$ETIQUETA_RAW" ] && [ -f /var/pawos/backup_etiqueta_auto.txt ]; then
    ETIQUETA_RAW=$(cat /var/pawos/backup_etiqueta_auto.txt)
fi
ETIQUETA=""
if [ -n "$ETIQUETA_RAW" ]; then
    ETIQUETA=$(printf '%s' "$ETIQUETA_RAW" | tr -c 'A-Za-z0-9_-' '_' | cut -c1-40)
fi
if [ -n "$ETIQUETA" ]; then
    NOMBRE_ARCHIVO="pawos_${FECHA}_${ETIQUETA}.db"
else
    NOMBRE_ARCHIVO="pawos_${FECHA}.db"
fi
if [ -f /var/pawos/pawos.db ]; then
    DB="/var/pawos/pawos.db"
else
    DB="pawos.db"
fi
if [ -f "$DB" ]; then
    rclone copyto "$DB" "$REMOTE/$NOMBRE_ARCHIVO"
    echo "[$(date)] Respaldo de base de datos subido: $NOMBRE_ARCHIVO"
else
    echo "[$(date)] No se encontro la base de datos, no se pudo respaldar."
fi
if [ -d /var/pawos/archivos/backups ]; then
    rclone copy /var/pawos/archivos/backups "$REMOTE/archivos_backups"
    echo "[$(date)] Carpeta de respaldos de archivos sincronizada."
fi
BACKUPEOF

cat > "$RAIZ/usr/local/bin/pawos-configurar-respaldo" << 'CONFEOF'
#!/bin/bash
set -e
MODO="$1"
HORAS="${2:-24}"
ESTADO_FILE="/var/pawos/backup_modo.txt"
mkdir -p /etc/systemd/system/pawos-backup.timer.d
mkdir -p /var/pawos
if [ "$MODO" = "manual" ]; then
    systemctl disable --now pawos-backup.timer 2>/dev/null || true
    rm -f /etc/systemd/system/pawos-backup.timer.d/override.conf
    systemctl daemon-reload
    echo "manual" > "$ESTADO_FILE"
    echo "Respaldo automatico desactivado. Ahora es manual (boton 'Respaldar ahora')."
    exit 0
fi
if [ "$MODO" = "auto" ]; then
    case "$HORAS" in
        ''|*[!0-9]*) echo "ERROR: horas debe ser un numero (ej. 24, 72, 168, 720)."; exit 1 ;;
    esac
    cat > /etc/systemd/system/pawos-backup.timer.d/override.conf << EOF
[Timer]
OnCalendar=
OnBootSec=
Persistent=
OnUnitActiveSec=${HORAS}h
Persistent=true
EOF
    systemctl daemon-reload
    systemctl enable --now pawos-backup.timer
    echo "automatico:${HORAS}" > "$ESTADO_FILE"
    echo "Respaldo automatico activado, cada ${HORAS} horas."
    exit 0
fi
echo "Uso: pawos-configurar-respaldo manual | auto <horas>"
exit 1
CONFEOF

cat > "$RAIZ/usr/local/bin/pawos-listar-respaldos" << 'LISTAEOF'
#!/bin/bash
set -e
REMOTE="ggdrive:PawOS_Backups"
rclone lsjson "$REMOTE" 2>/dev/null | python3 -c '
import json, re, sys
from datetime import datetime
try:
    datos = json.load(sys.stdin)
except Exception:
    datos = []
filas = [d for d in datos
         if not d.get("IsDir") and d.get("Name", "").startswith("pawos_")
         and d.get("Name", "").endswith(".db")]
filas.sort(key=lambda d: d.get("ModTime", ""), reverse=True)
patron = re.compile(r"^pawos_\d{8}_\d{6}_\d{3}(?:_(.+))?\.db$")
for d in filas:
    modtime = d.get("ModTime", "")
    try:
        dt = datetime.fromisoformat(modtime.replace("Z", "+00:00"))
        fecha = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        fecha = modtime
    tam = d.get("Size", 0)
    nombre = d.get("Name", "")
    m = patron.match(nombre)
    etiqueta = m.group(1) if (m and m.group(1)) else ""
    print(f"{fecha}\t{tam}\t{nombre}\t{etiqueta}")
'
LISTAEOF

cat > "$RAIZ/usr/local/bin/pawos-restaurar-nube" << 'RESTAUREOF'
#!/bin/bash
set -e
REMOTE_BASE="ggdrive:"
REMOTE="${REMOTE_BASE}PawOS_Backups"
ARCHIVO="$1"
if [ -z "$ARCHIVO" ]; then
    echo "Uso: pawos-restaurar-nube <archivo>"
    exit 1
fi
case "$ARCHIVO" in
    pawos_*.db) ;;
    *) echo "ERROR: nombre de archivo invalido (debe ser pawos_AAAAMMDD_HHMMSS[_ms].db)."; exit 1 ;;
esac
ID=$(rclone lsjson "$REMOTE" 2>/dev/null | python3 -c '
import json, sys
archivo = sys.argv[1]
try:
    datos = json.load(sys.stdin)
except Exception:
    datos = []
filas = [d for d in datos if not d.get("IsDir") and d.get("Name") == archivo]
filas.sort(key=lambda d: d.get("ModTime", ""), reverse=True)
if filas:
    print(filas[0].get("ID", ""))
' "$ARCHIVO")
if [ -z "$ID" ]; then
    echo "ERROR: no se encontro '$ARCHIVO' en Google Drive."
    exit 1
fi
mkdir -p /var/pawos
if [ -f /var/pawos/pawos.db ]; then
    cp /var/pawos/pawos.db "/var/pawos/pawos.db.antes-de-restaurar.$(date +%Y%m%d_%H%M%S)"
fi
TMP="/var/pawos/pawos.db.restaurando.tmp"
rm -f "$TMP"
rclone backend copyid "$REMOTE_BASE" "$ID" "$TMP"
mv "$TMP" /var/pawos/pawos.db
chown root:pawos-refugio /var/pawos/pawos.db
chmod 660 /var/pawos/pawos.db
echo "[$(date)] Base de datos restaurada desde $ARCHIVO (id $ID)"
RESTAUREOF

chmod 755 "$RAIZ/usr/local/bin/pawos-backup-nube" \
          "$RAIZ/usr/local/bin/pawos-configurar-respaldo" \
          "$RAIZ/usr/local/bin/pawos-listar-respaldos" \
          "$RAIZ/usr/local/bin/pawos-restaurar-nube"

echo "=== 6. Servicios systemd ==="
cat > "$RAIZ/etc/systemd/system/pawos-monitoreo.service" << 'EOF'
[Unit]
Description=PawOS - Servidor de Monitoreo (CPU, memoria, procesos via HTTP)
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/pawos-monitoreo
Restart=always
[Install]
WantedBy=multi-user.target
EOF
cat > "$RAIZ/etc/systemd/system/pawos-vacunas.service" << 'EOF'
[Unit]
Description=PawOS - Revision de vacunas pendientes
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/pawos-vacunas-check
EOF
cat > "$RAIZ/etc/systemd/system/pawos-vacunas.timer" << 'EOF'
[Unit]
Description=Ejecuta la revision de vacunas pendientes de PawOS una vez al dia
[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
cat > "$RAIZ/etc/systemd/system/pawos-backup.service" << 'EOF'
[Unit]
Description=PawOS - Respaldo a la nube (Google Drive via rclone)
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/pawos-backup-nube
EOF
cat > "$RAIZ/etc/systemd/system/pawos-backup.timer" << 'EOF'
[Unit]
Description=Ejecuta el respaldo a la nube de PawOS una vez al dia
[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF

echo "=== 7. Reglas de sudo (solo para lo necesario) ==="
cat > "$RAIZ/etc/sudoers.d/pawos-apagar" << 'EOF'
%pawos-admin ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-veterinario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-voluntario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
EOF
cat > "$RAIZ/etc/sudoers.d/pawos-respaldo" << 'EOF'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
EOF
chmod 440 "$RAIZ/etc/sudoers.d/pawos-apagar" "$RAIZ/etc/sudoers.d/pawos-respaldo"

echo "=== 8. Script postinst (se corre solo al instalar el .deb) ==="
cat > "$RAIZ/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

echo "Configurando PawOS Refugio..."

for g in pawos-admin pawos-veterinario pawos-voluntario pawos-refugio; do
    getent group "$g" >/dev/null || groupadd "$g"
done

mkdir -p /var/pawos/reportes
chown -R root:pawos-refugio /var/pawos
chmod -R 2770 /var/pawos

# Carpeta donde "Buscar Actualizaciones" (pawos-actualizar-gui) clona el
# repositorio. Sin esto, un usuario normal no tiene permiso de crear
# /opt/pawos-src (root:root, 755) y la actualizacion falla en silencio.
mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src

# A quien instalo el paquete (el usuario real detras de "sudo") se le
# da acceso automatico: sin esto, el respaldo en la nube y el acceso
# a la base de datos en /var/pawos no funcionarian para nadie.
USUARIO_REAL="${SUDO_USER:-}"
if [ -n "$USUARIO_REAL" ] && id "$USUARIO_REAL" &>/dev/null; then
    usermod -aG pawos-admin,pawos-refugio "$USUARIO_REAL"
    HOME_DIR=$(getent passwd "$USUARIO_REAL" | cut -d: -f6)
    for CARPETA in "$HOME_DIR/Escritorio" "$HOME_DIR/Desktop"; do
        if [ -d "$CARPETA" ]; then
            cp /usr/share/applications/pawos-refugio.desktop     "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-refugio-gui.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-apagar.desktop      "$CARPETA/" 2>/dev/null || true
            chmod +x "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            chown "$USUARIO_REAL":"$USUARIO_REAL" "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio-gui.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-apagar.desktop" metadata::trusted true 2>/dev/null || true
        fi
    done
    echo "Usuario '$USUARIO_REAL' agregado a los grupos pawos-admin y pawos-refugio."
    echo "IMPORTANTE: debe cerrar sesion y volver a entrar para que el cambio de grupo tome efecto."
fi

systemctl daemon-reload
systemctl enable --now pawos-monitoreo.service || true
systemctl enable --now pawos-vacunas.timer || true
systemctl enable --now pawos-backup.timer || true

if command -v ufw >/dev/null 2>&1; then
    ufw allow from 192.168.0.0/16 to any port 8080 proto tcp || true
    ufw allow from 10.0.0.0/8 to any port 8080 proto tcp || true
    ufw allow from 172.16.0.0/12 to any port 8080 proto tcp || true
fi

echo ""
echo "================================================="
echo " PawOS Refugio instalado correctamente."
echo " Abre 'PawOS Refugio (GUI)' desde el menu de aplicaciones."
echo " Dashboard de monitoreo: http://<ip-de-esta-maquina>:8080"
echo "================================================="

exit 0
EOF
chmod 755 "$RAIZ/DEBIAN/postinst"

echo "=== 9. Construyendo el .deb ==="
dpkg-deb --root-owner-group --build "$RAIZ" "$NOMBRE_DEB"

echo ""
echo "==========================================================="
echo " Listo: $NOMBRE_DEB"
echo ""
echo " Tus companeros lo instalan con:"
echo "   sudo apt install ./$NOMBRE_DEB"
echo " (apt instala solo las dependencias que falten; tambien pueden"
echo " hacer doble clic en el archivo desde el explorador de archivos"
echo " si su sistema tiene un instalador grafico de paquetes .deb)"
echo "==========================================================="
