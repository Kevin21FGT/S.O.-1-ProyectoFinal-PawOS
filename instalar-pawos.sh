#!/bin/bash
# instalar-pawos.sh
# Script de instalacion de PawOS sobre una instalacion normal de Debian 13 (Trixie).
# Correr como root: sudo bash instalar-pawos.sh
# Debe ejecutarse parado en la raiz del repositorio (donde estan las carpetas src/, include/, etc.)

set -e

if [ "$EUID" -ne 0 ]; then
    echo "Este script debe correr como root. Use: sudo bash instalar-pawos.sh"
    exit 1
fi

if [ ! -f "Makefile" ] && [ -f "live-build-config/Makefile" ]; then
    echo "Aviso: parece que estas en la raiz del repo pero el Makefile esta en live-build-config/."
    echo "Se usara live-build-config/ como directorio base."
    BASE="live-build-config"
else
    BASE="."
fi

if [ ! -f "$BASE/Makefile" ]; then
    echo "ERROR: no se encontro Makefile en '$BASE'. Corra este script desde la carpeta del repo."
    exit 1
fi

echo "=== 1. Instalando dependencias de compilacion y sistema ==="
apt-get update
apt-get install -y build-essential libncurses-dev libsqlite3-dev nasm ufw

echo "=== 2. Compilando PawOS desde el codigo fuente ==="
cd "$BASE"
make clean
make all
BINDIR="$(pwd)"
cd - >/dev/null

echo "=== 3. Copiando binarios a /usr/local/bin ==="
install -m 755 "$BINDIR/pawos-refugio"        /usr/local/bin/pawos-refugio
install -m 755 "$BINDIR/pawos-vacunas-check"  /usr/local/bin/pawos-vacunas-check
install -m 755 "$BINDIR/pawos-monitoreo"      /usr/local/bin/pawos-monitoreo

echo "=== 4. Creando script de respaldo a la nube (rclone) ==="
install -d /usr/local/bin
cat > /usr/local/bin/pawos-backup-nube << 'BACKUPEOF'
#!/bin/bash
# pawos-backup-nube - Respaldo de datos de PawOS a Google Drive (rclone).
# Requiere que 'rclone config' ya este configurado con el remote 'ggdrive'.
set -e
REMOTE="ggdrive:PawOS_Backups"
FECHA=$(date +%Y%m%d_%H%M%S)
if [ -f /var/pawos/pawos.db ]; then
    DB="/var/pawos/pawos.db"
else
    DB="pawos.db"
fi
if [ -f "$DB" ]; then
    rclone copyto "$DB" "$REMOTE/pawos_${FECHA}.db"
    echo "[$(date)] Respaldo de base de datos subido: pawos_${FECHA}.db"
else
    echo "[$(date)] No se encontro la base de datos, no se pudo respaldar."
fi
if [ -d /var/pawos/archivos/backups ]; then
    rclone copy /var/pawos/archivos/backups "$REMOTE/archivos_backups"
    echo "[$(date)] Carpeta de respaldos de archivos sincronizada."
fi
BACKUPEOF
chmod 755 /usr/local/bin/pawos-backup-nube

echo "=== 5. Creando grupos y usuarios de PawOS ==="
for g in pawos-admin pawos-veterinario pawos-voluntario; do
    getent group "$g" >/dev/null || groupadd "$g"
done
crear_usuario() {
    local user=$1 grupo=$2 pass=$3
    if ! id "$user" &>/dev/null; then
        useradd -m -G "$grupo" -s /bin/bash "$user"
        echo "${user}:${pass}" | chpasswd
        echo "Usuario creado: $user"
    else
        echo "Usuario ya existe, se omite: $user"
    fi
}
crear_usuario admin_refugio  pawos-admin       admin123
crear_usuario veterinario1   pawos-veterinario vet123
crear_usuario voluntario1    pawos-voluntario  vol123

echo "=== 6. Creando /var/pawos y permisos ==="
mkdir -p /var/pawos/reportes
chown -R root:pawos-admin /var/pawos
chmod -R 2770 /var/pawos

echo "=== 7. Configurando sudoers (solo apagar/reiniciar) ==="
mkdir -p /etc/sudoers.d
cat > /etc/sudoers.d/pawos-apagar << 'SUDOEOF'
%pawos-admin ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-veterinario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-voluntario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
SUDOEOF
chmod 440 /etc/sudoers.d/pawos-apagar

echo "=== 8. Instalando servicios systemd ==="
cat > /etc/systemd/system/pawos-monitoreo.service << 'EOF'
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

cat > /etc/systemd/system/pawos-vacunas.service << 'EOF'
[Unit]
Description=PawOS - Revision de vacunas pendientes
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/pawos-vacunas-check
EOF

cat > /etc/systemd/system/pawos-vacunas.timer << 'EOF'
[Unit]
Description=Ejecuta la revision de vacunas pendientes de PawOS una vez al dia
[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/pawos-backup.service << 'EOF'
[Unit]
Description=PawOS - Respaldo a la nube (Google Drive via rclone)
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/pawos-backup-nube
EOF

cat > /etc/systemd/system/pawos-backup.timer << 'EOF'
[Unit]
Description=Ejecuta el respaldo a la nube de PawOS una vez al dia
[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now pawos-monitoreo.service
systemctl enable --now pawos-vacunas.timer
systemctl enable --now pawos-backup.timer

echo "=== 9. Configurando firewall (ufw) ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.0.0/16 to any port 8080 proto tcp
ufw allow from 10.0.0.0/8 to any port 8080 proto tcp
ufw allow from 172.16.0.0/12 to any port 8080 proto tcp
ufw --force enable

echo "=== 10. Creando accesos directos de escritorio ==="
mkdir -p /usr/share/applications
cat > /usr/share/applications/pawos-refugio.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio
Exec=x-terminal-emulator -e /usr/local/bin/pawos-refugio
Terminal=false
Icon=utilities-terminal
Categories=Utility;
EOF

cat > /usr/share/applications/pawos-apagar.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Apagar PawOS
Exec=sudo /sbin/poweroff
Terminal=false
Icon=system-shutdown
Categories=Utility;
EOF

for u in admin_refugio veterinario1 voluntario1; do
    if id "$u" &>/dev/null; then
        home_dir=$(getent passwd "$u" | cut -d: -f6)
        mkdir -p "$home_dir/Desktop"
        cp /usr/share/applications/pawos-refugio.desktop "$home_dir/Desktop/"
        cp /usr/share/applications/pawos-apagar.desktop  "$home_dir/Desktop/"
        chmod +x "$home_dir/Desktop/"*.desktop
        chown -R "$u":"$u" "$home_dir/Desktop"
        gio set "$home_dir/Desktop/pawos-refugio.desktop" metadata::trusted true 2>/dev/null || true
        gio set "$home_dir/Desktop/pawos-apagar.desktop"  metadata::trusted true 2>/dev/null || true
    fi
done

echo ""
echo "================================================="
echo " Instalacion de PawOS completada."
echo " Usuarios creados: admin_refugio / veterinario1 / voluntario1"
echo " Dashboard de monitoreo: http://<ip-de-esta-maquina>:8080"
echo " (usuario: admin, contrasena: pawos2026)"
echo "================================================="
