
#!/bin/bash
# backup_nube.sh - Respaldo de datos de PawOS a Google Drive (rclone).
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
elif [ -d archivos_pawos/backups ]; then
    rclone copy archivos_pawos/backups "$REMOTE/archivos_backups"
    echo "[$(date)] Carpeta de respaldos de archivos (local) sincronizada."
fi
