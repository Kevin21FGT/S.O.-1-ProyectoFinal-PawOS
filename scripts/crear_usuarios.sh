#!/bin/bash
# crear_usuarios.sh - Crea los grupos de roles y usuarios de ejemplo de PawOS.
# Ejecutar como root dentro del sistema (o en el hook de live-build).

set -e

for g in pawos-admin pawos-veterinario pawos-voluntario; do
    getent group "$g" >/dev/null || groupadd "$g"
done

crear_usuario() {
    local user=$1 grupo=$2
    if ! id "$user" &>/dev/null; then
        useradd -m -G "$grupo" -s /bin/bash "$user"
        echo "Usuario $user creado (grupo $grupo). Defina su contrasena:"
        passwd "$user"
    fi
}

crear_usuario admin_refugio  pawos-admin
crear_usuario veterinario1   pawos-veterinario
crear_usuario voluntario1    pawos-voluntario

mkdir -p /var/pawos/reportes
chown -R root:pawos-admin /var/pawos
chmod -R 2770 /var/pawos

echo "Listo. Grupos y usuarios de PawOS creados."
