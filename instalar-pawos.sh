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
apt-get install -y build-essential libncurses-dev libsqlite3-dev nasm ufw libgtk-3-dev pkg-config libcrypt-dev python3 python3-pip rclone
# fpdf2: genera el PDF del recordatorio de citas (correo/WhatsApp).
pip3 install fpdf2 --break-system-packages || echo "AVISO: no se pudo instalar fpdf2. El PDF de citas no funcionara hasta correr: sudo pip3 install fpdf2 --break-system-packages"
echo "=== 2. Compilando PawOS desde el codigo fuente ==="
cd "$BASE"
make clean
make all
make gui
BINDIR="$(pwd)"
cd - >/dev/null
echo "=== 3. Copiando binarios a /usr/local/bin ==="
install -m 755 "$BINDIR/pawos-refugio"        /usr/local/bin/pawos-refugio
install -m 755 "$BINDIR/pawos-vacunas-check"  /usr/local/bin/pawos-vacunas-check
install -m 755 "$BINDIR/pawos-monitoreo"      /usr/local/bin/pawos-monitoreo
install -m 755 "$BINDIR/pawos-refugio-gui"    /usr/local/bin/pawos-refugio-gui

echo "=== 3b. Copiando scripts de recordatorio de citas (correo/WhatsApp) ==="
install -m 755 "$BINDIR/pawos-notificar-cita"               /usr/local/bin/pawos-notificar-cita
install -m 755 "$BINDIR/pawos-configurar-notificaciones"    /usr/local/bin/pawos-configurar-notificaciones
install -m 755 "$BINDIR/pawos-enviar-correo-cita"            /usr/local/bin/pawos-enviar-correo-cita
install -m 755 "$BINDIR/pawos-enviar-whatsapp-cita"          /usr/local/bin/pawos-enviar-whatsapp-cita
install -m 755 "$BINDIR/pawos-generar-pdf-cita.py"           /usr/local/bin/pawos-generar-pdf-cita.py

echo "=== 4. Creando script de respaldo a la nube (rclone) ==="
install -d /usr/local/bin
cat > /usr/local/bin/pawos-backup-nube << 'BACKUPEOF'
#!/bin/bash
# pawos-backup-nube - Respaldo de datos de PawOS a Google Drive (rclone).
# Requiere que 'rclone config' ya este configurado con el remote 'ggdrive'.
#
# Uso: pawos-backup-nube [etiqueta]
#   [etiqueta] es opcional (la usa el boton "Respaldar ahora" del GUI,
#   para poder reconocer un respaldo despues por nombre en vez de solo
#   por fecha). Si no se da ninguna (por ejemplo, en el respaldo
#   automatico diario de systemd, donde no hay nadie para escribirla),
#   se usa la ETIQUETA POR DEFECTO guardada en
#   /var/pawos/backup_etiqueta_auto.txt (la escribe el GUI al presionar
#   "Guardar configuracion" en la pantalla de Respaldo en la Nube). Si
#   tampoco hay una etiqueta por defecto guardada, el respaldo sale sin
#   etiqueta, igual que antes.
set -e
REMOTE="ggdrive:PawOS_Backups"
# Fecha con milisegundos (no solo segundos): Google Drive permite dos
# archivos con el nombre identico en la misma carpeta (a diferencia de
# un sistema de archivos normal), asi que si "Respaldar ahora" se
# dispara dos veces muy seguido, sin los milisegundos podrian terminar
# subiendose dos archivos con el mismo nombre - lo cual despues hace
# fallar la restauracion por nombre ambiguo (ver pawos-restaurar-nube).
FECHA=$(date +%Y%m%d_%H%M%S_%N); FECHA="${FECHA:0:19}"

ETIQUETA_RAW="$1"
if [ -z "$ETIQUETA_RAW" ] && [ -f /var/pawos/backup_etiqueta_auto.txt ]; then
    ETIQUETA_RAW=$(cat /var/pawos/backup_etiqueta_auto.txt)
fi

# Etiqueta opcional: solo letras/numeros/guion/guion_bajo, maximo 40
# caracteres, para que el nombre de archivo resultante sea siempre
# valido y facil de manejar. Si queda vacia (no se dio ninguna, ni
# explicita ni por defecto, o solo tenia caracteres invalidos), el
# nombre queda igual que antes.
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
chmod 755 /usr/local/bin/pawos-backup-nube
echo "=== 4b. Creando script para configurar el respaldo (automatico/manual) ==="
cat > /usr/local/bin/pawos-configurar-respaldo << 'CONFEOF'
#!/bin/bash
# pawos-configurar-respaldo - Cambia el respaldo a la nube entre modo
# Automatico (con el intervalo que elija el administrador) y Manual
# (el temporizador se apaga, solo se respalda cuando alguien le da
# "Respaldar ahora" desde la GUI).
#
# Uso:
#   pawos-configurar-respaldo manual
#   pawos-configurar-respaldo auto <horas>      (24=1 dia, 72=3 dias,
#                                                 168=1 semana, 720=1 mes)
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
chmod 755 /usr/local/bin/pawos-configurar-respaldo
echo "=== 4c. Creando script para listar el historial de respaldos ==="
cat > /usr/local/bin/pawos-listar-respaldos << 'LISTAEOF'
#!/bin/bash
# pawos-listar-respaldos - Muestra el registro de respaldos que ya
# existen en Google Drive (mas reciente primero), para que el GUI
# ("Respaldo en la Nube") pueda ofrecer restaurar alguno.
#
# Usa 'rclone lsjson' sin ningun filtro de rclone (--include,
# --files-only): en pruebas reales esos filtros resultaron poco
# confiables (un --include exacto por nombre dejaba pasar la carpeta
# "archivos_backups" que vive en la misma carpeta de Drive; combinado
# con --files-only, en cambio, no devolvia nada aunque el archivo si
# existiera). En vez de eso, se trae la lista completa sin filtrar y se
# filtra/ordena con Python (mas predecible).
#
# Salida: una linea por respaldo, con TABULADOR entre columnas (la
# fecha trae un espacio adentro, por eso no se separa por espacios):
#   <fecha, hora LOCAL de esta maquina>\t<tamano en bytes>\t<archivo>\t<etiqueta o vacio>
#
# La fecha se convierte de UTC (lo que da Drive) a la zona horaria
# local del sistema con datetime.astimezone() - antes se mostraba tal
# cual en UTC, lo cual no coincidia con la hora local ni con las demas
# fechas que muestra el GUI (esas si usan hora local, via systemctl).
#
# La etiqueta sale del nombre del archivo: "Respaldar ahora" puede
# guardar uno con un nombre extra al final, por ejemplo
# "pawos_20260815_180230_512_antes-de-prueba.db" -> etiqueta
# "antes-de-prueba". Los respaldos automaticos (sin etiqueta) quedan
# con el nombre de siempre, "pawos_20260815_180230_512.db".
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
chmod 755 /usr/local/bin/pawos-listar-respaldos
echo "=== 4d. Creando script para restaurar la base de datos desde la nube ==="
cat > /usr/local/bin/pawos-restaurar-nube << 'RESTAUREOF'
#!/bin/bash
# pawos-restaurar-nube - Restaura /var/pawos/pawos.db desde un respaldo
# especifico de Google Drive (el nombre EXACTO tiene que venir de
# 'pawos-listar-respaldos' o de la tabla del GUI - la fecha que se
# muestra ahi es la fecha de modificacion en Drive, no forma parte del
# nombre real del archivo, asi que no se debe reconstruir el nombre a
# mano a partir de la fecha). Antes de sobreescribir, guarda una copia
# de la base de datos actual (nunca se borra sola) por si el restore
# fue un error.
#
# Uso: pawos-restaurar-nube <archivo>   (ej. pawos_20260815_165651.db)
#
# Por que se restaura por ID y no por nombre/copyto: Google Drive
# permite que existan dos archivos con el nombre identico en la misma
# carpeta (no hay restriccion de unicidad como en un sistema de
# archivos normal), asi que pedirlo por nombre puede ser ambiguo. Y,
# como en pawos-listar-respaldos, los filtros de rclone (--include,
# --files-only) resultaron poco confiables en pruebas reales. Por eso
# aqui tambien se usa 'rclone lsjson' sin filtrar, se busca el ID unico
# con Python comparando el nombre exacto, y se restaura por ese ID con
# 'rclone backend copyid' (que si identifica un archivo sin ambiguedad).
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

# Restaura primero a un archivo temporal y solo al final lo pone en su
# lugar (mv): si "rclone backend copyid" fallara a medias, pawos.db
# real nunca queda a medio escribir.
TMP="/var/pawos/pawos.db.restaurando.tmp"
rm -f "$TMP"
rclone backend copyid "$REMOTE_BASE" "$ID" "$TMP"
mv "$TMP" /var/pawos/pawos.db
chown root:pawos-refugio /var/pawos/pawos.db
chmod 660 /var/pawos/pawos.db
echo "[$(date)] Base de datos restaurada desde $ARCHIVO (id $ID)"
RESTAUREOF
chmod 755 /usr/local/bin/pawos-restaurar-nube
echo "=== 5. Creando grupos y usuarios de PawOS ==="
for g in pawos-admin pawos-veterinario pawos-voluntario pawos-refugio; do
    getent group "$g" >/dev/null || groupadd "$g"
done
crear_usuario() {
    local user=$1 grupo=$2 pass=$3
    if ! id "$user" &>/dev/null; then
        useradd -m -G "$grupo,pawos-refugio" -s /bin/bash "$user"
        echo "${user}:${pass}" | chpasswd
        echo "Usuario creado: $user"
    else
        echo "Usuario ya existe, se omite: $user"
        usermod -aG pawos-refugio "$user"
    fi
}
crear_usuario admin_refugio  pawos-admin       admin123
crear_usuario veterinario1   pawos-veterinario vet123
crear_usuario voluntario1    pawos-voluntario  vol123
echo "=== 6. Creando /var/pawos y permisos ==="
mkdir -p /var/pawos/reportes
chown -R root:pawos-refugio /var/pawos
chmod -R 2770 /var/pawos

# Carpeta donde "Buscar Actualizaciones" (pawos-actualizar-gui) clona el
# repositorio. Sin esto, un usuario normal no tiene permiso de crear
# /opt/pawos-src (root:root, 755) y la actualizacion falla en silencio.
mkdir -p /opt/pawos-src
chown root:pawos-refugio /opt/pawos-src
chmod 2775 /opt/pawos-src

# Marca la carpeta como segura para TODOS los usuarios del equipo
# (escribe en /etc/gitconfig). Sin esto, git rechaza operar ahi con
# "posesion dudosa detectada" porque el dueno es root pero la usan
# usuarios normales -- y ese error se confunde con "sin conexion".
git config --system --add safe.directory /opt/pawos-src
echo "=== 7. Configurando sudoers (solo apagar/reiniciar) ==="
mkdir -p /etc/sudoers.d
cat > /etc/sudoers.d/pawos-apagar << 'SUDOEOF'
%pawos-admin ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-veterinario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
%pawos-voluntario ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot
SUDOEOF
chmod 440 /etc/sudoers.d/pawos-apagar
# Permiso aparte, solo para Administrador: disparar el respaldo manualmente
# (con o sin etiqueta), cambiar entre respaldo automatico/manual, y
# ver/restaurar el historial de respaldos, todo desde la pantalla
# "Respaldo en la Nube" del GUI, sin que la aplicacion tenga que pedir
# contrasena. "pawos-backup-nube" se agrega para que el boton "Respaldar
# ahora" pueda llamarlo directo (en un hilo aparte) y pasarle la
# etiqueta opcional; el "systemctl ... pawos-backup.service" se deja
# igual por compatibilidad (lo sigue usando el respaldo automatico).
cat > /etc/sudoers.d/pawos-respaldo << 'SUDOEOF2'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
SUDOEOF2
chmod 440 /etc/sudoers.d/pawos-respaldo
cat > /etc/sudoers.d/pawos-actualizar << 'SUDOEOF3'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
SUDOEOF3
chmod 440 /etc/sudoers.d/pawos-actualizar
cat > /etc/sudoers.d/pawos-notificaciones << 'SUDOEOF4'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/local/bin/pawos-configurar-notificaciones
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/local/bin/pawos-enviar-correo-cita, /usr/local/bin/pawos-enviar-whatsapp-cita
SUDOEOF4
chmod 440 /etc/sudoers.d/pawos-notificaciones
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
cat > /usr/share/applications/pawos-refugio-gui.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio (GUI)
Comment=Sistema de gestion para refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
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
        cp /usr/share/applications/pawos-refugio-gui.desktop "$home_dir/Desktop/"
        cp /usr/share/applications/pawos-apagar.desktop  "$home_dir/Desktop/"
        chmod +x "$home_dir/Desktop/"*.desktop
        chown -R "$u":"$u" "$home_dir/Desktop"
        gio set "$home_dir/Desktop/pawos-refugio.desktop" metadata::trusted true 2>/dev/null || true
        gio set "$home_dir/Desktop/pawos-refugio-gui.desktop" metadata::trusted true 2>/dev/null || true
        gio set "$home_dir/Desktop/pawos-apagar.desktop"  metadata::trusted true 2>/dev/null || true
    fi
done
echo ""
echo "================================================="
echo " Instalacion de PawOS completada."
echo " Usuarios creados: admin_refugio / veterinario1 / voluntario1"
echo " Dashboard de monitoreo: http://<ip-de-esta-maquina>:8080"
echo " (usuario: admin, contrasena: pawos2026)"
echo " GUI: pawos-refugio-gui   |   CLI: pawos-refugio"
echo "================================================="
