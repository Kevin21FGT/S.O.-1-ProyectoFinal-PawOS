# PawOS - Personalización del sistema operativo base

Este es el requisito individual de Kevin: **Personalización del sistema operativo base**. No se construyó una ISO nueva de instalación (se descartó el camino de `live-build` en una sesión anterior); en su lugar, el Debian 13 oficial ya instalado en la VM se personaliza con un script que aplica branding de PawOS sobre la instalación existente.

## 1. Qué incluye

| Cambio | Dónde queda | Efecto |
|---|---|---|
| Banner de bienvenida en consola | `/etc/issue` | Se ve antes de iniciar sesión en una terminal de texto (Ctrl+Alt+F2, o consola serial). |
| Mensaje al iniciar sesión | `/etc/motd` | Se ve al abrir una terminal nueva o conectarse por SSH: lista los comandos y servicios de PawOS. |
| Nombre visible del sistema | `/etc/os-release` (`PRETTY_NAME`) | Lo que muestran comandos como `hostnamectl` o `cat /etc/os-release`. Se deja `ID=debian` intacto para no romper nada que dependa de detectar la distro base (apt, systemd, etc.) — solo cambia el nombre "amigable". |
| Nombre en el menú de arranque | `/etc/default/grub` (`GRUB_DISTRIBUTOR`) | Al reiniciar la VM, el menú de GRUB dice "PawOS - Refugio de Animales" en vez de "Debian GNU/Linux". |
| Fondo de pantalla | `/usr/share/backgrounds/pawos-wallpaper.png` | Aplicado vía `gsettings` a los 4 usuarios del sistema (`vboxuser`, `admin_refugio`, `veterinario1`, `voluntario1`). |
| Acceso directo de escritorio | `/usr/share/applications/pawos-refugio-gui.desktop` + copia en el escritorio de cada usuario | Ícono para abrir `pawos-refugio-gui` con doble clic, sin necesidad de terminal. |

## 2. Archivos de este entregable

- `pawos-wallpaper.png` — fondo de pantalla (1920x1080), generado con la paleta verde bosque que ya usa la GUI.
- `pawos-icon.png` — ícono de PawOS (256x256, fondo transparente), usado en el acceso directo.
- `personalizar_pawos.sh` — script que aplica todos los cambios de la tabla de arriba. Es seguro correrlo más de una vez.

## 3. Cómo aplicarlo en la VM

```bash
cp -r /media/sf_compartido/branding ~/S.O.-1-ProyectoFinal-PawOS/
cd ~/S.O.-1-ProyectoFinal-PawOS/branding
chmod +x personalizar_pawos.sh
sudo ./personalizar_pawos.sh
```

Para ver los cambios:

- **MOTD**: abre una terminal nueva.
- **Fondo de pantalla**: si el usuario con el que corriste `sudo` tiene sesión gráfica abierta ahora mismo, se aplica al toque; si no, ese usuario debe correr una vez, ya en su propia sesión:
  ```bash
  gsettings set org.gnome.desktop.background picture-uri 'file:///usr/share/backgrounds/pawos-wallpaper.png'
  ```
- **Menú de GRUB**: reinicia la VM (`sudo reboot`) y fíjate en el menú de arranque antes de que cargue el sistema.
- **Acceso directo**: revisa el escritorio de cada usuario — debería aparecer el ícono "PawOS Refugio".

## 4. Por qué no se hizo una ISO nueva

Se evaluó usar `live-build` para generar una imagen `.iso` de Debian ya personalizada de fábrica (como una versión "remasterizada" de Debian), pero se descartó: agrega bastante complejidad y tiempo de compilación sin aportar algo que el profesor no pueda ver igual de bien corriendo la VM ya personalizada en vivo. El camino elegido — Debian oficial + script de personalización — cumple el requisito ("personalización del sistema operativo base") de forma más simple y 100% reproducible con un solo comando.
