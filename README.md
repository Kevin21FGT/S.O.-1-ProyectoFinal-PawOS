# PawOS — Sistema Operativo para Refugios de Animales

Proyecto final de Sistemas Operativos I (UMG). PawOS es una personalización de **Debian GNU/Linux 13 (Trixie)** enfocada en la causa **Protección Animal**: un sistema completo, listo para instalar, para que un refugio de animales gestione mascotas, vacunas, adopciones, donantes y reportes, con todos los conceptos de sistemas operativos vistos en el curso aplicados sobre una app real.

PawOS no es una distribución armada desde cero: es Debian 13 oficial, con un programa propio (CLI y GUI), personalización visual, servicios, scripts de automatización y una ISO instalable armada con `live-build` + Calamares.

## Índice

- [De cero a un sistema operativo funcionando](#de-cero-a-un-sistema-operativo-funcionando)
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

## De cero a un sistema operativo funcionando

Esta sección resume, en orden, todo el camino desde el código fuente (C + Ensamblador) hasta tener PawOS corriendo como un sistema operativo real. Cada paso enlaza con la sección donde está explicado a detalle.

**1. El código fuente son dos lenguajes distintos, compilados por separado.** La lógica del programa está en C (`src/*.c`); una sola pieza, el cálculo del checksum de integridad, está escrita directamente en Ensamblador x86-64 (`src/checksum.asm`). `gcc` compila cada `.c` a un objeto `.o`; `nasm` compila el `.asm` a otro objeto `.o` (mismo formato, ELF64). Ver [Compilar desde el código fuente](#compilar-desde-el-código-fuente) para los comandos, y [Integridad de datos](#módulos-del-programa) para el detalle exacto de cómo se enlazan ambos lenguajes en un solo binario.

**2. El enlazador (`gcc`, usado como *linker*) une todos los `.o` en binarios ejecutables.** De ahí salen cuatro programas: `pawos-refugio` (CLI), `pawos-refugio-gui` (GUI, requiere además las librerías de GTK3), `pawos-vacunas-check` (demonio de vacunas) y `pawos-monitoreo` (servidor HTTP). En este punto ya se puede correr PawOS directamente (`./pawos-refugio`), pero todavía no es "un sistema operativo": es solo un programa suelto sobre cualquier Linux con las librerías necesarias.

**3. Convertir esos binarios en un sistema operativo instalado** es trabajo de `instalar-pawos.sh` (ver [Instalar PawOS sobre un Debian ya instalado](#instalar-pawos-sobre-un-debian-ya-instalado)): compila todo lo del paso 1-2, copia los binarios a `/usr/local/bin` (para que estén en el `PATH` de cualquier usuario), crea los usuarios/grupos de Linux reales (`admin_refugio`, etc.), registra los servicios de `systemd` para que el vigilante de vacunas y el respaldo corran solos, configura el firewall, y deja accesos directos en el escritorio. A partir de aquí, PawOS ya es parte del sistema operativo Debian que lo hospeda, no un programa aparte.

**4. Empacar todo eso en una ISO booteable** es el trabajo de `live-build` (ver [Construir la ISO instalable](#construir-la-iso-instalable) y `live-iso/README_live_iso.md`): arma una imagen de Debian 13 desde cero, con los paquetes necesarios ya incluidos (`live-iso/package-lists/pawos.list.chroot`), y unos *hooks* (`live-iso/hooks/*.hook.chroot`) que corren automáticamente durante la construcción y hacen, dentro de esa imagen, básicamente lo mismo que `instalar-pawos.sh` (compilar, crear usuarios, servicios, permisos), más el branding visual (fondo de pantalla, logo, GRUB) y el instalador gráfico Calamares.

**5. Booteando esa ISO** se obtiene un Debian en vivo con PawOS ya instalado y funcionando (sin tocar el disco todavía — es una demo/prueba). Para dejarlo instalado de forma permanente en una máquina o VM, se usa el ícono "Instalar PawOS" del escritorio (Calamares), que copia el sistema completo al disco duro. Ese sistema instalado ya es, en todo el sentido de la palabra, un sistema operativo: arranca solo, tiene sus propios usuarios y permisos, corre sus propios servicios en segundo plano, y sigue funcionando igual después de apagarlo y prenderlo de nuevo.

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

**Cómo se enlaza el Ensamblador con el C, exactamente:**

`checksum.asm` define una sola rutina, `pawos_checksum`, con esta firma equivalente en C:

```c
uint64_t pawos_checksum(const unsigned char *datos, size_t len);
```

El algoritmo, instrucción por instrucción: por cada byte del arreglo `datos`, rota el acumulador (`rax`) 5 bits a la izquierda (`rol rax, 5`) y le hace XOR con el byte actual (`xor rax, rdx`). Al final, `rax` (que en la convención de llamadas de Linux x86-64, System V AMD64, es donde va el valor de retorno de una función) contiene el checksum de 64 bits. Los dos parámetros llegan en registros, no en la pila: `rdi` trae el puntero `datos` y `rsi` trae `len` — así es como System V AMD64 pasa el primer y segundo argumento de cualquier función, sea C o Ensamblador.

Gracias a que ambos lados (el código que genera `gcc` a partir de los `.c`, y el código que genera `nasm` a partir del `.asm`) respetan esa misma convención y el mismo formato de archivo objeto (ELF64), no hace falta ningún "pegamento" especial para unirlos:

1. `nasm -f elf64 src/checksum.asm -o src/checksum.o` — convierte el Ensamblador en un archivo objeto ELF64, con `pawos_checksum` marcada como símbolo `global` (visible desde fuera, para que otros `.o` lo puedan referenciar).
2. `include/checksum.h` declara esa misma función con `extern` del lado de C, para que el compilador sepa que existe aunque no vea su código fuente.
3. `integridad.c` la llama como cualquier función normal: `uint64_t resultado = pawos_checksum(buf, usado);` (usando el contenido del respaldo de donantes como `datos`).
4. En el paso final, `gcc` no compila el `.asm` — solo **enlaza** `checksum.o` junto con todos los `.o` de C en un solo binario (`gcc $(OBJ) $(ASM_OBJ) -o pawos-refugio $(LDFLAGS)`). Para el enlazador, un símbolo es un símbolo: no le importa si el `.o` vino de C o de Ensamblador, siempre que los nombres y la convención de llamada coincidan.

`integridad_actualizar_checksum_donantes()` guarda ese resultado en un archivo (`donantes.checksum`); `integridad_verificar_donantes()` (nombre real puede variar, ver `integridad.c`) vuelve a calcularlo y lo compara — si no coinciden, alguien modificó la base de donantes por fuera del programa.

## Personalización del sistema (branding)

`branding/personalizar_pawos.sh` aplica, sobre un Debian 13 ya instalado: fondo de pantalla y logo propios, mensaje de `/etc/issue` y `/etc/motd`, nombre del sistema en `/etc/os-release`, nombre en el menú de arranque de GRUB, y accesos directos de escritorio para cada usuario.

## Instalar PawOS sobre un Debian ya instalado

```bash
cd S.O.-1-ProyectoFinal-PawOS
sudo bash instalar-pawos.sh
```

Este script (pensado para correr sobre una instalación normal de Debian 13) hace todo de una vez: instala las librerías necesarias, compila el CLI y el GUI, instala los binarios en `/usr/local/bin`, crea los tres usuarios y sus grupos, crea `/var/pawos` con los permisos correctos, instala y habilita los servicios de systemd, configura el firewall, y crea los accesos directos de escritorio.

## Construir la ISO instalable

Esto arma un archivo `.iso` real: al arrancarlo (DVD, USB, o unidad óptica virtual) carga directo un escritorio Debian + GNOME con PawOS ya compilado, con los tres usuarios y todos los servicios listos, más un ícono "Instalar PawOS" en el escritorio que copia el sistema completo al disco de forma permanente (vía Calamares). No modifica ni reemplaza `instalar-pawos.sh`; es un proceso aparte, pensado para generar un medio de instalación distribuible.

Usa la herramienta `live-build` de Debian, que arma la imagen paquete por paquete (no clona una ISO existente): descarga Debian 13 desde los repositorios oficiales, instala GNOME y las dependencias, y encima corre los **hooks** propios de PawOS (scripts que viven en `live-iso/hooks/`) dentro de ese sistema recién armado, antes de sellarlo en el `.iso` final.

### 1. Requisito de espacio

Se necesita una partición o disco aparte con al menos ~30 GB libres, montado por ejemplo en `/mnt/build` — la imagen completa de Debian + GNOME + PawOS ocupa bastante mientras se arma.

### 2. Instalar `live-build`

```bash
sudo apt update
sudo apt install -y live-build
```

### 3. Preparar la configuración

```bash
mkdir -p /mnt/build/pawos-live
cd /mnt/build/pawos-live

lb config \
  --distribution trixie \
  --archive-areas "main contrib non-free non-free-firmware" \
  --binary-images iso-hybrid \
  --debian-installer none

mkdir -p config/package-lists config/hooks/normal config/includes.chroot
cp live-iso/package-lists/*.chroot config/package-lists/
cp live-iso/hooks/*.chroot config/hooks/normal/
cp -r live-iso/includes.chroot/* config/includes.chroot/
chmod +x config/hooks/normal/*.hook.chroot
```

`lb config` define el "molde" de la imagen (Debian 13/Trixie, con los repositorios `contrib`/`non-free` habilitados para drivers, formato ISO híbrido que sirve tanto para DVD como para USB, y sin el instalador de texto de Debian porque PawOS trae el suyo propio con Calamares).

**Paso importante que no se automatiza:** el hook `0100-pawos-instalar.hook.chroot` compila PawOS desde `/opt/pawos` **dentro** de la imagen, así que el código fuente actualizado hay que copiarlo ahí también, antes de construir:

```bash
cp -r ~/S.O.-1-ProyectoFinal-PawOS/* config/includes.chroot/opt/pawos/
```

(Se hace así, copiando el repo local ya actualizado, en vez de que el hook clone desde GitHub durante la construcción, para no depender de credenciales de git ni de que el repo remoto esté disponible en ese momento.)

### 4. Qué hace cada hook, en orden

`live-build` corre los hooks en orden alfabético por su prefijo numérico:

| Hook | Qué hace |
|---|---|
| `0100-pawos-instalar.hook.chroot` | Compila PawOS (`make all && make gui`) desde `/opt/pawos`, instala los binarios en `/usr/local/bin`, crea los tres usuarios y grupos, agrega `admin_refugio` al grupo `sudo` (necesario para Calamares), instala los servicios de systemd (solo `enable`, no `--now`, porque el chroot no tiene un systemd real corriendo), configura sudoers y firewall. |
| `0200-pawos-branding.hook.chroot` | Aplica la personalización visual: `/etc/issue`, `/etc/motd`, `PRETTY_NAME` en `/etc/os-release`, y corrige permisos de los archivos de branding (fondo de pantalla, iconos) para que no queden ilegibles por el usuario de la sesión. |
| `0900-pawos-fix-permisos-final.hook.chroot` | Pasada final de permisos (por si algo llegó restringido vía `includes.chroot`), quita el asistente de bienvenida de GNOME (`gnome-initial-setup`/`gnome-tour`), y agrega el acceso directo "Instalar PawOS" (Calamares) al escritorio de los tres usuarios. Corre último a propósito, para pisar cualquier permiso incorrecto que hayan dejado los hooks anteriores. |

### 5. Construir la ISO

Tarda bastante (baja el sistema completo de GNOME desde los repositorios de Debian, compila PawOS, aplica todos los hooks) — de 30 minutos a más de una hora, según la conexión. Necesita permisos de root reales (no `sudo -n`, porque manipula el sistema de archivos a bajo nivel):

```bash
cd /mnt/build/pawos-live
sudo lb build 2>&1 | tee build.log
```

Si algo falla, el error queda al final de `build.log`. Al terminar, el archivo queda en esa misma carpeta, con un nombre como `live-image-amd64.hybrid.iso`.

### 6. Probarla

Antes de usarla como entrega final, se prueba arrancándola en una VM nueva (no la de desarrollo, para no arriesgar nada):

1. Crear una VM nueva en VirtualBox.
2. Montar `live-image-amd64.hybrid.iso` como unidad óptica (IDE, no SATA — más confiable en VirtualBox).
3. Arrancar y confirmar: que carga el escritorio con el fondo de pantalla de PawOS, que se puede iniciar sesión con `admin_refugio` / `veterinario1` / `voluntario1`, que `pawos-refugio-gui` abre y funciona, y que el ícono "Instalar PawOS" deja el sistema instalado de forma permanente en el disco virtual.

### 7. Para USB booteable (opcional)

Con Rufus (Windows): seleccionar el `.iso`, modo "DD Image" (no "ISO normal", para que quede booteable como sistema live) y grabarlo en el USB.

### 8. Si el código cambia después

Como el código se copia una sola vez a `config/includes.chroot/opt/pawos/` en el paso 3, si el repositorio se actualiza hay que repetir ese `cp` con el código nuevo y volver a correr `sudo lb build` (o `sudo lb clean && sudo lb build` para forzar que se vuelva a descargar todo desde cero) para que la ISO quede al día.

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

### Cómo funciona por debajo

El script `/usr/local/bin/pawos-backup-nube` (instalado por `instalar-pawos.sh`) hace el trabajo real: copia `/var/pawos/pawos.db` a Google Drive con `rclone copyto` (nombrando el archivo con fecha y hora, `pawos_AAAAMMDD_HHMMSS.db`, para no pisar respaldos anteriores) y sincroniza la carpeta `/var/pawos/archivos/backups` con `rclone copy`. Usa un remote de `rclone` llamado `ggdrive`, que apunta a una cuenta real de Google Drive.

Ese script lo ejecuta el servicio systemd `pawos-backup.service` (`Type=oneshot`, corre una vez y termina), disparado por el timer `pawos-backup.timer`. El servicio corre como **root**, así que la configuración de `rclone` que usa es la de la cuenta root (`/root/.config/rclone/rclone.conf`), no la del usuario que inició sesión gráficamente — importante tenerlo en cuenta si algún día hay que reconfigurar la cuenta de Drive:

```bash
sudo rclone config    # crear/editar el remote "ggdrive"
```

Confirmado funcionando en la práctica: cada corrida sube el archivo y termina en pocos segundos (`sudo journalctl -u pawos-backup.service` para ver el historial completo, con hora exacta de cada respaldo).

### Pantalla "Respaldo en la Nube" del GUI (`abrir_pantalla_respaldo` en `main_gtk.c`)

Accesible para cualquier rol, pero solo **admin_refugio** puede tocar los controles (el resto los ve deshabilitados con un tooltip "Requiere rol Administrador" — mismo patrón que las pantallas de Procesos y Memoria). Tiene tres secciones:

**Estado actual** — dos etiquetas de solo lectura que se llenan preguntándole a systemd (`systemctl show ... --value -p ActiveState/Result/LastTriggerUSec`), sin necesitar permisos especiales porque es una consulta, no una acción:
- "Último respaldo automático": la última vez que se disparó el timer.
- "Estado del servicio: `<ActiveState>` | Resultado: `<Result>`" — por ejemplo `inactive` / `success` cuando ya terminó bien, o `activating` mientras sigue corriendo.

**Configuración del respaldo** — dos radio buttons controlan el modo:
- **Automático** — habilita un combo box con 4 intervalos (Cada 1 día / 3 días / 1 semana / 1 mes, que internamente son 24/72/168/720 horas).
- **Manual (solo con 'Respaldar ahora')** — deshabilita el combo; el respaldo solo corre si alguien lo dispara a mano.

Al presionar "Guardar configuración", el GUI llama (vía `sudo -n`, sin pedir contraseña) al script `/usr/local/bin/pawos-configurar-respaldo`:
- `pawos-configurar-respaldo manual` → apaga y deshabilita `pawos-backup.timer`, borra el *override* de horario si existía.
- `pawos-configurar-respaldo auto <horas>` → escribe un *override* de systemd en `/etc/systemd/system/pawos-backup.timer.d/override.conf` (limpia el `OnCalendar` original de "todos los días a las 11pm" y lo reemplaza por `OnUnitActiveSec=<horas>h`, es decir "cada tantas horas desde la última vez que corrió"), recarga systemd y habilita el timer.

En ambos casos el script deja registrado el modo elegido en `/var/pawos/backup_modo.txt` (por ejemplo `manual` o `automatico:72`), que es lo que el GUI vuelve a leer cada vez que abre la pantalla para mostrar el modo actual ya seleccionado.

**Botones inferiores**:
- "Actualizar estado" — vuelve a consultar systemd y refresca las dos etiquetas de arriba.
- "Respaldar ahora" — dispara `sudo -n systemctl --no-block start pawos-backup.service`. La bandera `--no-block` es importante: sin ella, `systemctl start` espera a que el servicio termine por completo antes de devolver el control, lo cual congelaba la ventana entre 20 y 30 segundos (todo el programa se queda esperando esa única llamada, porque la GUI es de un solo hilo). Con `--no-block`, systemd solo encola la orden y el botón responde al instante; el resultado real hay que verlo después con "Actualizar estado".
- "Cerrar" — cierra la ventana.

### Permisos (sudoers)

Todo esto funciona sin pedir contraseña gracias a una regla específica en `/etc/sudoers.d/pawos-respaldo`, que solo aplica al grupo `pawos-admin` (o sea, solo `admin_refugio`) y solo para estos dos comandos exactos:

```
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo
```

Si algún día se cambian los argumentos de cualquiera de esos dos comandos en el código C, hay que actualizar esta línea de sudoers para que coincida exactamente, o `sudo -n` fallará en silencio (sin pedir contraseña, pero sin ejecutar nada).

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
