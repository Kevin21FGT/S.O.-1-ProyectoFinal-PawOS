#!/bin/bash
# ============================================================
# personalizar_pawos.sh - Personalizacion del sistema operativo
# base (requisito "Personalizacion del sistema operativo base"
# del proyecto final). Aplica branding de PawOS sobre un Debian
# 13 oficial ya instalado: banner de bienvenida (MOTD), mensaje
# de login (/etc/issue), nombre visible del sistema (os-release),
# nombre en el menu de arranque (GRUB), fondo de pantalla y un
# acceso directo de escritorio para abrir la GUI de PawOS.
#
# No reinstala nada ni reemplaza el Debian base: solo cambia
# archivos de configuracion y agrega los dos PNG de branding.
# Seguro de correr mas de una vez (sobreescribe los mismos
# archivos con el mismo contenido).
#
# Uso:
#   chmod +x personalizar_pawos.sh
#   sudo ./personalizar_pawos.sh
# ============================================================
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Este script necesita sudo. Uso: sudo ./personalizar_pawos.sh"
    exit 1
fi

DIR_BRANDING="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WALLPAPER_ORIGEN="$DIR_BRANDING/pawos-wallpaper.png"
ICON_ORIGEN="$DIR_BRANDING/pawos-icon.png"

if [ ! -f "$WALLPAPER_ORIGEN" ] || [ ! -f "$ICON_ORIGEN" ]; then
    echo "No se encontraron pawos-wallpaper.png / pawos-icon.png junto a este script."
    echo "Asegurate de correrlo desde la carpeta branding/ copiada del shared folder."
    exit 1
fi

echo "1) Copiando imagenes de branding a /usr/share/backgrounds y /usr/share/icons..."
install -m 644 -D "$WALLPAPER_ORIGEN" /usr/share/backgrounds/pawos-wallpaper.png
install -m 644 -D "$ICON_ORIGEN" /usr/share/icons/pawos-icon.png

echo "2) Configurando /etc/issue (mensaje antes del login en consola)..."
cat > /etc/issue << 'EOF'
   ____                 ___  ____
  |  _ \ __ ___      __/ _ \/ ___|
  | |_) / _` \ \ /\ / / | | \___ \
  |  __/ (_| |\ V  V /| |_| |___) |
  |_|   \__,_| \_/\_/  \___/|____/

  PawOS - Sistema para Refugio de Animales
  Basado en Debian GNU/Linux 13 (Trixie)
  Proyecto Final - Sistemas Operativos I - UMG

EOF

echo "3) Configurando /etc/motd (mensaje despues del login, SSH y terminal)..."
cat > /etc/motd << 'EOF'
====================================================================
  PawOS - Sistema Operativo para Refugio de Animales
====================================================================
  Modulos disponibles:
    pawos-refugio          -> interfaz de texto (CLI)
    pawos-refugio-gui       -> interfaz grafica (GTK3)
    systemctl status pawos-monitoreo   -> servidor/dashboard (puerto 8080)
    systemctl status pawos-backup      -> respaldo automatico nocturno
    systemctl status pawos-tunnel      -> publicacion en la nube (Cloudflare)

  Usuarios de la aplicacion (dentro de PawOS, no del sistema):
    admin_refugio / veterinario1 / voluntario1

  Repositorio: github.com/Kevin21FGT/S.O.-1-ProyectoFinal-PawOS
====================================================================
EOF

echo "4) Ajustando el nombre visible del sistema (/etc/os-release, PRETTY_NAME)..."
if grep -q "^PRETTY_NAME=" /etc/os-release; then
    sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="PawOS 1.0 (basado en Debian GNU\/Linux 13)"/' /etc/os-release
else
    echo 'PRETTY_NAME="PawOS 1.0 (basado en Debian GNU/Linux 13)"' >> /etc/os-release
fi
# Se deja ID=debian intacto a proposito: asi apt, systemd y demas
# herramientas que dependen de detectar la distro base siguen
# funcionando normal. Solo se personaliza el nombre visible.

echo "5) Configurando el nombre en el menu de arranque (GRUB)..."
if [ -f /etc/default/grub ]; then
    if grep -q "^GRUB_DISTRIBUTOR=" /etc/default/grub; then
        sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="PawOS - Refugio de Animales"/' /etc/default/grub
    else
        echo 'GRUB_DISTRIBUTOR="PawOS - Refugio de Animales"' >> /etc/default/grub
    fi
    update-grub
else
    echo "   Aviso: no se encontro /etc/default/grub, se omite este paso."
fi

echo "6) Configurando fondo de pantalla (GNOME, para todos los usuarios ya creados)..."
for usuario in vboxuser admin_refugio veterinario1 voluntario1; do
    if id "$usuario" &>/dev/null; then
        sudo -u "$usuario" dbus-launch gsettings set org.gnome.desktop.background picture-uri "file:///usr/share/backgrounds/pawos-wallpaper.png" 2>/dev/null || true
        sudo -u "$usuario" dbus-launch gsettings set org.gnome.desktop.background picture-uri-dark "file:///usr/share/backgrounds/pawos-wallpaper.png" 2>/dev/null || true
        echo "   Fondo aplicado (o intentado) para: $usuario"
    fi
done
echo "   Nota: si algun usuario no tiene sesion grafica activa en este momento,"
echo "   gsettings puede no aplicar el cambio ahi. Ese usuario puede correrlo"
echo "   el mismo, ya con su sesion abierta:"
echo "   gsettings set org.gnome.desktop.background picture-uri 'file:///usr/share/backgrounds/pawos-wallpaper.png'"

echo "7) Creando acceso directo de escritorio para pawos-refugio-gui..."
cat > /usr/share/applications/pawos-refugio-gui.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio
Comment=Sistema de gestion para refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
Icon=/usr/share/icons/pawos-icon.png
Terminal=false
Categories=Utility;
EOF
chmod 644 /usr/share/applications/pawos-refugio-gui.desktop

for usuario in vboxuser admin_refugio veterinario1 voluntario1; do
    home_dir=$(eval echo "~$usuario")
    if [ -d "$home_dir/Desktop" ] || [ -d "$home_dir/Escritorio" ]; then
        escritorio="$home_dir/Desktop"
        [ -d "$home_dir/Escritorio" ] && escritorio="$home_dir/Escritorio"
        cp /usr/share/applications/pawos-refugio-gui.desktop "$escritorio/"
        chmod +x "$escritorio/pawos-refugio-gui.desktop"
        chown "$usuario":"$usuario" "$escritorio/pawos-refugio-gui.desktop"
        gio set "$escritorio/pawos-refugio-gui.desktop" metadata::trusted true 2>/dev/null || true
        echo "   Acceso directo copiado al escritorio de: $usuario"
    fi
done

echo ""
echo "Listo. Cambios aplicados:"
echo "  - /etc/issue y /etc/motd (banners de bienvenida)"
echo "  - /etc/os-release (PRETTY_NAME)"
echo "  - /etc/default/grub (nombre en el menu de arranque, tras reiniciar)"
echo "  - Fondo de pantalla PawOS"
echo "  - Icono de PawOS Refugio en el escritorio y menu de aplicaciones"
echo ""
echo "Para ver el nuevo /etc/issue: reinicia o abre una terminal en consola (Ctrl+Alt+F2)."
echo "Para ver el nuevo menu de GRUB: reinicia la VM."
echo "Para ver el MOTD nuevo: abre una terminal nueva o conectate por SSH de nuevo."
