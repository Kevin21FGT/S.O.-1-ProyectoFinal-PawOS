# PawOS — Sistema Operativo para Refugios de Animales

Proyecto final de Sistemas Operativos I (UMG). PawOS es una personalización de **Debian GNU/Linux 13 (Trixie)** enfocada en la causa **Protección Animal**: un sistema completo, listo para instalar, para que un refugio de animales gestione mascotas, vacunas, adopciones, donantes y reportes, con todos los conceptos de sistemas operativos vistos en el curso aplicados sobre una app real.

PawOS no es una distribución armada desde cero: es Debian 13 oficial, con un programa propio (CLI y GUI), personalización visual, servicios, scripts de automatización y una ISO instalable armada con `live-build` + Calamares.

## Índice

- [Estructura del proyecto](#estructura-del-proyecto)
- [Compilar desde el código fuente](#compilar-desde-el-código-fuente)
- [Usuarios y roles](#usuarios-y-roles)
- [Base de datos](#base-de-datos)
- [Módulos del programa](#módulos-del-programa)
- [Personalización del sistema (branding)](#personalización-del-sistema-branding)
- [Instalar PawOS sobre un Debian ya instalado](#instalar-pawos-sobre-un-debian-ya-instalado)
- [Construir la ISO instalable](#construir-la-iso-instalable)
- [Servicios del sistema (systemd)](#servicios-del-sistema-systemd)
- [Seguridad — estado actual](#seguridad--estado-actual)
- [Respaldo en la nube — estado actual](#respaldo-en-la-nube--estado-actual)
- [Requerimientos mínimos del curso — checklist](#requerimientos-mínimos-del-curso--checklist)

## Estructura del proyecto

```
S.O.-1-ProyectoFinal-PawOS/
├── Makefile                    # compila el CLI, el GUI, el demonio y el servidor
├── instalar-pawos.sh           # instala PawOS sobre un Debian 13 ya instalado
├── include/                    # headers (.h) de todos los modulos
├── src/                        # codigo fuente (.c y .asm)
├── branding/                   # wallpaper, icono, script de personalizacion visual
└── live-iso/                   # configuracion para armar la ISO instalable (live-build)
    ├── package-lists/          # que paquetes de Debian se instalan en la ISO
    ├── hooks/                  # scripts que corren durante la construccion de la ISO
    └── includes.chroot/        # archivos que se copian tal cual dentro de la ISO
```

### Archivos fuente, uno por uno

| Archivo | Qué hace |
|---|---|
| `main.c` | Punto de entrada del programa de **texto** (CLI). Inicializa la base de datos, la memoria y los archivos, muestra el login y el menú principal. |
| `main_gtk.c` | Punto de entrada del programa **gráfico** (GUI, GTK3). Mismo programa, pero con ventanas en vez de pantallas de texto. |
| `db.c` / `db.h` | Toda la base de datos SQLite: crea las tablas, y tiene las funciones para agregar/listar/actualizar/eliminar mascotas, vacunas, adopciones, donantes, alertas y notas. |
| `auth.c` / `auth.h` | Determina el **rol** del usuario mirando a qué grupo de Linux pertenece (usado por el GUI). |
| `pantalla_login.c` | Pantalla de usuario/contraseña que usa el **CLI** (consulta la tabla `usuarios` de la base de datos). |
| `ui.c` / `pantallas.c` | Piezas reutilizables de interfaz de texto (menús, mensajes, formularios) y las pantallas del CLI. |
| `procesos.c` / `pantalla_procesos.c` | Administración de procesos: lista procesos reales de Linux, permite crear uno de ejemplo y terminar procesos. |
| `memoria.c` / `pantalla_memoria.c` | Simulador de memoria virtual con paginación, marcos físicos y swap a disco. |
| `archivos.c` / `pantalla_archivos.c` | Organiza los archivos del refugio en carpetas por categoría y genera respaldos de la base de datos. |
| `servidor_monitoreo.c` | Servidor HTTP que muestra un dashboard con el estado del sistema (CPU, memoria, disco, procesos) y recibe alertas de sensores. |
| `vacunas_demonio.c` | Programa pequeño que revisa vacunas pendientes/vencidas; pensado para correr solo, vía un timer de systemd. |
| `integridad.c` / `checksum.asm` | Verifica que la base de datos de donantes no haya sido alterada, usando una rutina de checksum escrita en Ensamblador x86-64. |

## Compilar desde el código fuente

Necesitas estar parado en la raíz del repositorio (donde está el `Makefile`).

```bash
sudo apt install build-essential libncurses-dev libsqlite3-dev libgtk-3-dev pkg-config nasm

make clean       # borra binarios y .o de compilaciones anteriores
make all         # compila el CLI (pawos-refugio), el demonio de vacunas
                 # (pawos-vacunas-check) y el servidor de monitoreo (pawos-monitoreo)
make gui         # compila ademas la interfaz grafica (pawos-refugio-gui)
```

`make all` no incluye el GUI a propósito (para no obligar a instalar GTK3 si solo quieres el CLI). `make gui` es un objetivo aparte que se agrega sin tocar nada de lo anterior.

Para correrlo directo, sin instalar nada del sistema (útil para probar en tu laptop):

```bash
./pawos-refugio       # version de texto (ncurses)
./pawos-refugio-gui    # version grafica (GTK3)
```

Si no existe `/var/pawos/pawos.db` (por ejemplo, probando fuera de la ISO), el programa usa automáticamente `./pawos.db` en la carpeta actual.

## Usuarios y roles

PawOS crea tres usuarios reales de Linux, cada uno en un grupo distinto:

| Usuario | Contraseña | Grupo Linux | Rol dentro del programa |
|---|---|---|---|
| `admin_refugio` | `admin123` | `pawos-admin` (+ `sudo`) | Administrador: acceso total, incluye Memoria e instalar el sistema |
| `veterinario1` | `vet123` | `pawos-veterinario` | Veterinario: acceso a todo lo clínico |
| `voluntario1` | `vol123` | `pawos-voluntario` | Voluntario: solo ver/registrar mascotas y vacunas |

**Importante — dos mecanismos de permisos conviven en el código:**

- El **GUI** (`main_gtk.c`) usa `auth.c`, que mira el grupo real de Linux del usuario que inició sesión (`auth_rol_actual()`). Esto es "gestión de usuarios y permisos" a nivel del sistema operativo de verdad.
- El **CLI** (`main.c`) usa `pantalla_login.c`, que pide usuario/contraseña **dentro del programa** y los compara contra la tabla `usuarios` de la base de datos (`usuario_autenticar()` en `db.c`).

Es decir, el CLI tiene su propio login independiente del sistema operativo. Funciona, pero es importante saberlo porque significa que hay dos "bases de verdad" distintas para los roles (los grupos de Linux, y la tabla `usuarios`) — quedan sincronizadas manualmente (mismos tres usuarios en ambos lados), no automáticamente.

## Base de datos

SQLite, un solo archivo (`/var/pawos/pawos.db` en la ISO, o `./pawos.db` en pruebas locales). Tablas principales:

- **mascotas** — nombre, especie, raza, edad, estado (`disponible`/`en_proceso`/`adoptado`/`tratamiento`), fecha de ingreso.
- **vacunas** — asociada a una mascota, nombre de la vacuna, fecha de aplicación, próxima fecha, observaciones.
- **adopciones** — asociada a una mascota, datos del adoptante, fecha (al registrarla, marca la mascota como `adoptado`).
- **donantes** — nombre, contacto, monto donado, fecha.
- **usuarios** — username, password, rol (usada solo por el login del CLI).
- **alertas_sensores** — alertas que manda un sensor ESP32 externo (ver más abajo).
- **notas_veterinario** — notas clínicas libres por mascota.

El esquema se crea automáticamente la primera vez que corre cualquiera de los programas (`db_init()` en `db.c`), y las migraciones a bases de datos ya existentes (por ejemplo, agregar una columna nueva a una tabla vieja) se hacen con `ALTER TABLE` de forma aditiva, sin borrar nada de lo que ya había.

## Módulos del programa

### Gestión de mascotas, vacunas, adopciones, donantes y reportes

El núcleo de la aplicación (la parte específica de la causa "Protección Animal"). Disponible tanto en CLI como en GUI, con las mismas reglas de negocio (por ejemplo, adoptar una mascota automáticamente cambia su estado). Los reportes se generan como archivo `.txt` con el resumen del refugio.

### Administración de procesos (`procesos.c`)

Lee la carpeta `/proc` de Linux directamente (no usa `ps` ni ninguna herramienta externa) para listar los procesos reales que están corriendo en el sistema, con su PID, nombre y estado (`Ejecutando`, `Durmiendo`, `Zombie`, etc.). También permite:

- Crear un proceso hijo de ejemplo (`fork()` real) que simula una tarea de respaldo y escribe en un log.
- Terminar un proceso por su PID, con señal `SIGTERM` (normal) o `SIGKILL` (forzado).

### Manejo de memoria (`memoria.c`)

Un simulador de memoria virtual "de verdad" (a pequeña escala, para poder mostrarlo): 4 MB de RAM simulada, dividida en páginas de 4 KB. Cada proceso tiene su propia tabla de páginas. Cuando la memoria se llena, usa un algoritmo tipo reloj/segunda oportunidad para decidir qué página sacar de RAM, la guarda en un archivo de swap en disco (`refugio_swap.bin`), y la trae de vuelta automáticamente si se vuelve a necesitar — igual que hace un sistema operativo real cuando se queda sin RAM.

### Sistema de archivos organizado (`archivos.c`)

Organiza todo lo que el refugio guarda en carpetas por categoría dentro de `/var/pawos/archivos`: `mascotas`, `vacunas`, `adopciones`, `donantes`, `reportes`, `backups`. Permite listar archivos (con tamaño y fecha), eliminarlos, ver cuánto espacio ocupa cada categoría, y generar un respaldo con fecha y hora de la base de datos completa.

### Servidor de monitoreo (`servidor_monitoreo.c`)

Un servidor HTTP propio (sin frameworks, sockets directos) que corre en el puerto **8080** y expone un dashboard HTML con CPU, memoria, swap, espacio en disco, tiempo activo y procesos — leído directo de `/proc`. Requiere autenticación básica HTTP.

También expone `POST /api/alerta`, un endpoint sin autenticación pensado para que un sensor **ESP32** externo (por ejemplo, un collar con sensores de temperatura o movimiento) reporte posibles señales de lesión o maltrato; cada alerta que llega se guarda en la tabla `alertas_sensores` y aparece en el módulo "Alertas de Sensores" del CLI/GUI.

### Automatización (`vacunas_demonio.c` + `pawos-backup-nube`)

`pawos-vacunas-check` es un programa pequeño que revisa la base de datos en busca de vacunas pendientes o vencidas y genera una alerta (consola + log), sin que nadie tenga que entrar al programa. Corre solo, todos los días a las 8:00 AM, vía un timer de systemd (ver siguiente sección). `pawos-backup-nube` hace lo mismo pero para subir un respaldo de la base de datos a Google Drive (ver sección de nube).

### Integridad de datos (`integridad.c` + `checksum.asm`)

Verifica que la base de datos de donantes no se haya modificado por fuera del programa, calculando un checksum (rotación + XOR byte por byte) escrito directamente en **Ensamblador x86-64** (`checksum.asm`), y comparándolo contra el último checksum guardado.

## Personalización del sistema (branding)

`branding/personalizar_pawos.sh` aplica, sobre un Debian 13 ya instalado: fondo de pantalla y logo propios, mensaje de `/etc/issue` y `/etc/motd`, nombre del sistema en `/etc/os-release`, nombre en el menú de arranque de GRUB, y accesos directos de escritorio para cada usuario.

## Instalar PawOS sobre un Debian ya instalado

```bash
cd S.O.-1-ProyectoFinal-PawOS
sudo bash instalar-pawos.sh
```

Este script (pensado para correr sobre una instalación normal de Debian 13) hace todo de una vez: instala las librerías necesarias, compila el CLI y el GUI, instala los binarios en `/usr/local/bin`, crea los tres usuarios y sus grupos, crea `/var/pawos` con los permisos correctos, instala y habilita los servicios de systemd, configura el firewall, y crea los accesos directos de escritorio.

## Construir la ISO instalable

Para entregar PawOS como una ISO booteable (arranca directo a un escritorio PawOS ya funcionando, con un ícono "Instalar PawOS" para copiarlo de forma permanente al disco vía Calamares), ver la guía completa dentro de `live-iso/README_live_iso.md`. En resumen usa `live-build`, con la configuración de paquetes y los hooks que están en esa misma carpeta.

## Servicios del sistema (systemd)

| Servicio | Qué hace | Se activa |
|---|---|---|
| `pawos-monitoreo.service` | Corre el servidor de monitoreo (puerto 8080) | Al iniciar el sistema, siempre activo |
| `pawos-vacunas.timer` | Revisa vacunas pendientes | Todos los días a las 8:00 AM |
| `pawos-backup.timer` | Sube respaldo a la nube | Automático o manual, configurable desde el GUI (ver abajo) |
| `ufw` (firewall) | Solo permite el puerto 8080 desde redes locales (192.168.x.x, 10.x.x.x, 172.16-31.x.x) | Al iniciar el sistema |

## Seguridad — estado actual

Lo que **sí** está implementado: firewall configurado (ufw), permisos de sudo restringidos por usuario (solo apagar/reiniciar, excepto `admin_refugio` que también puede usar el instalador), y verificación de integridad de la base de donantes por checksum.

Lo que **falta** (pendiente, útil dejarlo anotado para la entrega): las contraseñas se guardan en **texto plano**, tanto en la tabla `usuarios` de la base de datos (login del CLI) como en el servidor de monitoreo (usuario/contraseña fijos en el código fuente: `admin` / `pawos2026`). Para una versión de producción real, lo correcto sería guardar un *hash* (por ejemplo con `bcrypt` o `crypt()`) en vez del texto plano.

## Respaldo en la nube — estado actual

El script `pawos-backup-nube` sube la base de datos y la carpeta de respaldos de archivos a Google Drive usando `rclone`, con un remote llamado `ggdrive` configurado (`rclone config`) en la cuenta de **root** (`/root/.config/rclone/rclone.conf`), ya que el servicio corre como root. Confirmado funcionando: cada corrida sube el archivo y termina en pocos segundos (ver logs con `sudo journalctl -u pawos-backup.service`).

Desde la pantalla "Respaldo en la Nube" del GUI (solo visible/editable para `admin_refugio`), se puede elegir entre dos modos:

- **Automático** — corre solo, con el intervalo que elija el administrador: cada 1 día, 3 días, 1 semana o 1 mes. Internamente ajusta `pawos-backup.timer` con un *override* de systemd (`/etc/systemd/system/pawos-backup.timer.d/override.conf`, con `OnUnitActiveSec`).
- **Manual** — el timer se desactiva; el respaldo solo corre cuando alguien presiona "Respaldar ahora" (dispara `pawos-backup.service` una sola vez, sin esperar).

El cambio de modo lo hace el script `/usr/local/bin/pawos-configurar-respaldo` (`manual` o `auto <horas>`), invocado por el GUI vía `sudo` sin contraseña (regla específica en `/etc/sudoers.d/pawos-respaldo`, solo para el grupo `pawos-admin`). El botón "Respaldar ahora" usa `systemctl --no-block start pawos-backup.service` para no congelar la interfaz mientras el respaldo corre en segundo plano; el estado real se consulta después con "Actualizar estado".

Si se instala PawOS en una máquina nueva, ese `rclone config` sí hay que volver a correrlo una vez (no viaja con el código, es una credencial local de cada instalación):

```bash
sudo rclone config    # crear un remote llamado "ggdrive" apuntando a Google Drive
```

## Requerimientos mínimos del curso — checklist

| Requerimiento | Estado |
|---|---|
| Personalización del sistema operativo base | Completo |
| Gestión de usuarios y permisos | Completo (ver nota sobre los dos mecanismos, arriba) |
| Administración de procesos | Completo |
| Manejo de memoria | Completo |
| Sistema de archivos organizado | Completo |
| Scripts de automatización | Completo |
| Servicios del sistema | Completo |
| Seguridad básica | Parcial (falta hashear contraseñas) |
| Interfaz de usuario (CLI y gráfica) | Completo |
| Servidor para monitorear | Completo |
| Alojarlo en la nube | Completo (automático/manual desde el GUI, `rclone` configurado y funcionando) |
| Git con historial de commits | Completo |
| Documentación técnica y manual de usuario | Este documento |
| Registro de mascotas | Completo |
| Agenda de vacunas | Completo |
| Control de adopciones | Completo |
| Base de datos de donantes | Completo |
| Reportes automáticos | Completo |

## Equipo

Proyecto Final — Sistemas Operativos I — Universidad Mariano Gálvez de Guatemala.
