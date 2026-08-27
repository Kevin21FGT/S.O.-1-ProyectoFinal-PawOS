# PawOS - ISO instalable/booteable (live-build)

Este entregable arma un archivo `.iso` real de PawOS: al arrancarlo (DVD o USB), carga directo un escritorio GNOME con PawOS ya instalado, compilado, con los tres usuarios y todos los servicios listos — sin que nadie tenga que instalar nada a mano.

No modifica ni reemplaza `instalar-pawos.sh` (ese script sigue igual, para instalar PawOS sobre un Debian ya instalado). Este es un proceso aparte, específico para generar la ISO.

## 1. Requisito de espacio

Se necesita un disco/partición aparte con al menos ~30 GB libres, montado en `/mnt/build` (ver pasos que ya hicimos: agregar disco virtual, `parted`, `mkfs.ext4`, `mount`).

## 2. Instalar live-build

```bash
sudo apt update
sudo apt install -y live-build
```

## 3. Copiar esta carpeta y armar la configuración

```bash
mkdir -p /mnt/build/pawos-live
cp -r /media/sf_compartido/live-iso /mnt/build/pawos-live/live-iso-fuente
cd /mnt/build/pawos-live

lb config \
  --distribution trixie \
  --archive-areas "main contrib non-free non-free-firmware" \
  --binary-images iso-hybrid \
  --debian-installer none

mkdir -p config/package-lists config/hooks/normal config/includes.chroot
cp live-iso-fuente/package-lists/*.chroot config/package-lists/
cp live-iso-fuente/hooks/*.chroot config/hooks/normal/
cp -r live-iso-fuente/includes.chroot/* config/includes.chroot/
chmod +x config/hooks/normal/*.hook.chroot
```

**Paso adicional obligatorio:** el hook `0100-pawos-instalar.hook.chroot` compila PawOS desde `/opt/pawos` dentro de la imagen (no clona nada de GitHub durante el build, para no depender de credenciales ni de que el repo remoto esté disponible en ese momento). Por eso el código fuente actualizado hay que copiarlo ahí antes de construir:

```bash
mkdir -p config/includes.chroot/opt/pawos
cp -r ~/S.O.-1-ProyectoFinal-PawOS/* config/includes.chroot/opt/pawos/
```

## 4. Construir la ISO

Esto tarda bastante (baja el sistema completo de GNOME desde los repositorios de Debian, compila PawOS, aplica todo) — dependiendo de tu conexión, puede ser de 30 minutos a más de una hora. Necesita permisos de root de verdad:

```bash
cd /mnt/build/pawos-live
sudo lb build 2>&1 | tee build.log
```

Si algo falla, el error va a estar al final de `build.log` — mándamelo y lo revisamos.

Al terminar, el archivo queda en la misma carpeta, con un nombre como `live-image-amd64.hybrid.iso`.

## 5. Probarla

Antes de usarla para la entrega, pruébala arrancándola en una VM nueva (no la actual, para no arriesgar tu proyecto):

1. Crea una VM nueva en VirtualBox (puede ser temporal, para la prueba).
2. Monta `live-image-amd64.hybrid.iso` como unidad óptica.
3. Arráncala y confirma: que carga el escritorio, que aparece el fondo de pantalla de PawOS, que puedes iniciar sesión con `admin_refugio` / `veterinario1` / `voluntario1`, y que `pawos-refugio-gui` abre y funciona.

## 6. Para USB booteable (opcional, si la ingeniera pide probarla en una compu física)

Con Rufus (Windows): selecciona el `.iso`, modo "DD Image" (no ISO normal, para que sea booteable como sistema live), y grábalo en el USB.

## 7. Qué incluye la imagen

- Debian 13 (Trixie) + escritorio GNOME completo.
- PawOS compilado desde el repositorio (`rama-Combinada`, la rama del equipo ya integrada): CLI, GUI, demonio de vacunas, servidor de monitoreo.
- Los tres usuarios de la aplicación (`admin_refugio`, `veterinario1`, `voluntario1`) con sus grupos y permisos.
- Servicios systemd (`pawos-monitoreo`, `pawos-vacunas.timer`) habilitados, arrancan solos al primer inicio real.
- Firewall (`ufw`) configurado.
- Branding: fondo de pantalla, banner de login, mensaje de bienvenida, nombre del sistema.
- Accesos directos de escritorio para CLI, GUI y apagar.

## 8. Nota importante

Como el código se copia una sola vez a `config/includes.chroot/opt/pawos/` (paso 3), la ISO refleja el código que estaba ahí en el momento del `cp`, no lo último de `rama-Combinada` automáticamente. Si el equipo sigue subiendo cambios después, hay que repetir ese `cp` con el código actualizado y volver a correr `sudo lb build` (o `sudo lb clean && sudo lb build` para forzar que se descargue todo desde cero) para que la ISO quede al día.
