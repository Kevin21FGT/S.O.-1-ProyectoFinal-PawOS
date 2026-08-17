# PawOS — Sistema Operativo para Refugios de Animales

Proyecto final de Sistemas Operativos I (UMG). PawOS es una personalización de **Debian GNU/Linux 13 (Trixie)** enfocada en la causa **Protección Animal**: un sistema completo, listo para instalar, para que un refugio de animales gestione mascotas, vacunas, adopciones, donantes y reportes, con todos los conceptos de sistemas operativos vistos en el curso aplicados sobre una app real.

PawOS no es una distribución armada desde cero: es Debian 13 oficial, con un programa propio (CLI y GUI), personalización visual, servicios, scripts de automatización y una ISO instalable armada con `live-build` + Calamares.

## Índice

- [De cero a un sistema operativo funcionando](#de-cero-a-un-sistema-operativo-funcionando)
- [Requisitos del sistema y librerías](#requisitos-del-sistema-y-librerías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Compilar desde el código fuente](#compilar-desde-el-código-fuente)
- [Usuarios y roles](#usuarios-y-roles)
- [Base de datos](#base-de-datos)
- [Módulos del programa](#módulos-del-programa)
- [Personalización del sistema (branding)](#personalización-del-sistema-branding)
- [Instalar PawOS sobre un Debian ya instalado](#instalar-pawos-sobre-un-debian-ya-instalado)
- [Construir la ISO instalable](#construir-la-iso-instalable)
- [Servicios del sistema (systemd)](#servicios-del-sistema-systemd)
- [Actualizaciones automáticas (botón "Buscar Actualizaciones")](#actualizaciones-automáticas-botón-buscar-actualizaciones)
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

## Requisitos del sistema y librerías

### Hardware mínimo

PawOS corre sobre Debian 13 + escritorio GNOME completo, así que hereda los requisitos de eso (GNOME es el componente más pesado, no PawOS en sí):

| Recurso | Mínimo | Recomendado |
|---|---|---|
| Arquitectura | x86-64 (amd64) | x86-64 (amd64) |
| RAM | 2 GB | 4 GB o más |
| Disco (sistema ya instalado) | 10 GB | 20 GB o más |
| Disco (solo para *armar* la ISO, aparte) | — | ~30 GB libres, ver [Construir la ISO instalable](#construir-la-iso-instalable) |

### Paquetes del sistema operativo base (Debian 13)

Estos son los paquetes de Debian que se instalan (ya sea con `instalar-pawos.sh` o dentro de la ISO vía `live-iso/package-lists/pawos.list.chroot`) para tener un sistema completo, más allá de PawOS mismo:

| Paquete | Para qué es |
|---|---|
| `task-gnome-desktop` | El escritorio GNOME completo (solo en la ISO; sobre una Debian ya instalada se asume que ya existe un entorno gráfico) |
| `network-manager` / `network-manager-applet` | Manejo de red (WiFi/Ethernet) con interfaz gráfica |
| `sudo` | Permite a los usuarios de PawOS ejecutar comandos puntuales como root (apagar, reiniciar, instalar, respaldar) |
| `git` | Control de versiones (para trabajar sobre el código fuente) |
| `ufw` | Firewall (ver [Firewall](#seguridad--estado-actual)) |
| `sqlite3` | Cliente de línea de comandos de SQLite (para inspeccionar `pawos.db` manualmente si hace falta) |
| `calamares` / `calamares-settings-debian` | Instalador gráfico (solo en la ISO, para dejar PawOS instalado de forma permanente) |

### Librerías para compilar y correr PawOS (nuestro programa)

Estos son los paquetes que el propio código de PawOS necesita — para compilarlo (`-dev`) y, en tiempo de ejecución, la librería compartida correspondiente:

| Paquete (compilación) | Para qué lo usa PawOS |
|---|---|
| `build-essential` | `gcc`, `make` y las herramientas básicas para compilar C |
| `libncurses-dev` | Interfaz de texto del CLI (`pawos-refugio`): menús, formularios, colores en la terminal |
| `libsqlite3-dev` | Base de datos (`db.c`) — mascotas, vacunas, adopciones, donantes, usuarios, alertas |
| `libgtk-3-dev` | Interfaz gráfica del GUI (`pawos-refugio-gui`); trae consigo (como dependencias) GLib, Pango, Cairo, GdkPixbuf, AT-SPI/ATK, HarfBuzz — todo lo que GTK3 necesita para dibujar ventanas, texto y widgets |
| `pkg-config` | Herramienta que le dice al compilador dónde están los headers y librerías de GTK3 (`pkg-config --cflags/--libs gtk+-3.0`) |
| `nasm` | Ensamblador: compila `checksum.asm` a un objeto ELF64 (ver [De cero a un sistema operativo funcionando](#de-cero-a-un-sistema-operativo-funcionando)) |
| `libcrypt-dev` | Hasheo de contraseñas con `crypt()` (SHA-512) — ver [Seguridad](#seguridad--estado-actual) |
| `python3` | No lo usa el programa en C, pero sí los scripts `pawos-listar-respaldos`/`pawos-restaurar-nube` (ver [Respaldo en la nube](#respaldo-en-la-nube--estado-actual)), para filtrar el listado de respaldos de Google Drive de forma confiable. Normalmente ya viene con Debian + GNOME, pero `instalar-pawos.sh` lo pide explícitamente por si acaso. |

En tiempo de ejecución, el `Makefile` enlaza cada binario con `-lncurses -lsqlite3 -lm -lcrypt` (CLI/demonio/monitor) o con las librerías de GTK3 que entrega `pkg-config` (GUI) — `-lm` es la librería matemática de C (siempre disponible con glibc, usada por ejemplo en los cálculos de porcentajes de CPU/memoria del servidor de monitoreo).

> **Nota:** estas librerías de compilación (`build-essential`, `libncurses-dev`, `libsqlite3-dev`, `libgtk-3-dev`, `pkg-config`, `nasm`) además de `git`, ya no son solo para quien desarrolla PawOS en su propia máquina — la ISO instalable también las incluye, porque el botón "Buscar Actualizaciones" del GUI recompila el programa directo en el equipo del usuario final (ver [Actualizaciones automáticas](#actualizaciones-automáticas-botón-buscar-actualizaciones)).

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
- El **CLI** (`main.c`) usa `pantalla_login.c`, que pide usuario/contraseña **dentro del programa** y la verifica contra la tabla `usuarios` de la base de datos (`usuario_autenticar()` en `db.c`) — la contraseña se guarda como *hash* (`crypt()`, SHA-512), nunca en texto plano; ver [Seguridad — estado actual](#seguridad--estado-actual) para el detalle completo.

Es decir, el CLI tiene su propio login independiente del sistema operativo. Funciona, pero es importante saberlo porque significa que hay dos "bases de verdad" distintas para los roles (los grupos de Linux, y la tabla `usuarios`) — quedan sincronizadas manualmente (mismos tres usuarios en ambos lados), no automáticamente.

## Base de datos

SQLite, un solo archivo (`/var/pawos/pawos.db` en la ISO, o `./pawos.db` en pruebas locales). Tablas principales:

- **mascotas** — nombre, especie, raza, edad, estado (`disponible`/`en_proceso`/`adoptado`/`tratamiento`), fecha de ingreso.
- **vacunas** — asociada a una mascota, nombre de la vacuna, fecha de aplicación, próxima fecha, observaciones.
- **adopciones** — asociada a una mascota, datos del adoptante, fecha (al registrarla, marca la mascota como `adoptado`).
- **donantes** — nombre, contacto, monto donado, fecha.
- **usuarios** — username, password (guardada como *hash* SHA-512 vía `crypt()`, no en texto plano), rol (usada solo por el login del CLI).
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

Un servidor HTTP propio (sin frameworks, sockets directos) que corre en el puerto **8080** y expone un dashboard HTML con CPU, memoria, swap, espacio en disco, tiempo activo y procesos — leído directo de `/proc`. Requiere autenticación básica HTTP; la contraseña se verifica contra un *hash* (`crypt()`, SHA-512) guardado en el código, no contra el texto plano — ver [Seguridad — estado actual](#seguridad--estado-actual).

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

**Importante: esto solo aplica a la ISO como archivo — no a un PawOS que ya está instalado.** La ISO es únicamente el medio de instalación inicial. Una vez que Calamares deja el sistema instalado en un disco (real o virtual), ese PawOS instalado es un Debian normal con los binarios en `/usr/local/bin`, sin ninguna relación directa con el `.iso` del que vino. Actualizarlo con una corrección de código funciona exactamente igual que en cualquier instalación hecha con `instalar-pawos.sh` (ver [Compilar desde el código fuente](#compilar-desde-el-código-fuente)): reemplazar los archivos fuente, `make clean && make all && make gui`, y copiar los binarios nuevos (o volver a correr `instalar-pawos.sh`). No hace falta rearmar la ISO ni reinstalar el sistema operativo completo.

Rearmar la ISO (este proceso de `lb build`) solo hace falta cuando se necesita una imagen instalable *nueva y actualizada* — por ejemplo, para instalar PawOS desde cero en otra máquina, para el USB de entrega final, o para que quien instale desde la ISO reciba ya la última versión del código. Para seguir desarrollando y probando sobre un PawOS que ya está instalado y corriendo, ese paso se puede saltar por completo.

## Servicios del sistema (systemd)

| Servicio | Qué hace | Se activa |
|---|---|---|
| `pawos-monitoreo.service` | Corre el servidor de monitoreo (puerto 8080) | Al iniciar el sistema, siempre activo |
| `pawos-vacunas.timer` | Revisa vacunas pendientes | Todos los días a las 8:00 AM |
| `pawos-backup.timer` | Sube respaldo a la nube | Automático o manual, configurable desde el GUI (ver abajo) |
| `ufw` (firewall) | Solo permite el puerto 8080 desde redes locales (192.168.x.x, 10.x.x.x, 172.16-31.x.x) | Al iniciar el sistema |

## Actualizaciones automáticas (botón "Buscar Actualizaciones")

Además de reconstruir la ISO completa (ver sección anterior), PawOS Refugio tiene un mecanismo para actualizarse a sí mismo desde dentro del GUI, sin reinstalar el sistema operativo ni volver a grabar ningún medio — pensado para que, una vez que un refugio ya tiene PawOS instalado, reciba correcciones de código sin necesitar volver a pasar por Calamares.

### Qué hace

Un botón "🔄 Buscar Actualizaciones" en el menú principal del GUI (`main_gtk.c`, junto a "Salir") abre una terminal y corre `/usr/local/bin/pawos-actualizar-gui`, que:

1. Revisa si hay una versión más nueva del código en el repositorio remoto.
2. Si la hay, muestra un resumen de las novedades (los mensajes de commit nuevos) antes de instalar nada.
3. Descarga el código, recompila el CLI y el GUI (`make` / `make gui`), e instala los binarios nuevos en `/usr/local/bin`.
4. Si algo falla en cualquier paso (sin internet, error de compilación, sin permisos), se conserva la versión que ya estaba funcionando y se muestra un mensaje de error claro — nunca deja el sistema a medio actualizar.

### Diseño "de programa comercial" (sin exponer el repositorio)

A pedido explícito del equipo, el actualizador se comporta como el de cualquier programa comercial (Windows Update, actualizador de una app de escritorio): el usuario final nunca ve la URL del repositorio de GitHub ni el nombre de la rama, ni en la salida de la terminal ni mirando el código del script — ambos datos están codificados en base64 dentro de `pawos-actualizar-gui` en vez de aparecer como texto plano.

### Requisito nuevo en la ISO: herramientas de compilación

Como la actualización recompila el programa **en la máquina del usuario final** (no descarga un binario ya compilado), la ISO tiene que traer instaladas las mismas herramientas que antes solo hacían falta en la máquina de quien desarrolla PawOS (ver la nota al final de [Requisitos del sistema y librerías](#requisitos-del-sistema-y-librerías)): `git`, `build-essential`, `pkg-config`, `libgtk-3-dev`, `libsqlite3-dev`, `libncurses-dev` y `nasm`.

### Permisos: por qué hace falta `/opt/pawos-src` y una regla de sudoers

El código se clona/actualiza en una carpeta fija del sistema, `/opt/pawos-src` (dueño `root:pawos-refugio`, permisos `2775` con *setgid*), en vez de en el `$HOME` de cada usuario — así, sin importar si actualiza `admin_refugio`, `veterinario1` o `voluntario1`, siempre es la misma ruta, lo que permite escribir una regla de `sudoers` con rutas exactas (`/etc/sudoers.d/pawos-actualizar`) que solo autoriza, sin pedir contraseña, los comandos puntuales para instalar el binario nuevo en `/usr/local/bin` — nada más.

Como `/opt/pawos-src` lo crea `root` pero lo usan usuarios normales, git bloquea las operaciones ahí por seguridad ("posesión dudosa" / *dubious ownership*, protección agregada en versiones recientes de git); `pawos-actualizar-gui` se registra a sí mismo como excepción (`git config --global --add safe.directory`) automáticamente la primera vez que corre, sin que el usuario tenga que hacer nada a mano.

### Por qué se instala con `cp` + `mv` en vez de `cp` directo

El binario que se está actualizando (`pawos-refugio-gui`) normalmente sigue *corriendo* mientras el usuario usa el botón (abrió el actualizador desde dentro del programa). Sobreescribirlo directo con `cp` falla con `Text file busy`, porque Linux no deja modificar el contenido de un ejecutable que está en memoria en ese momento. La solución: copiar el binario nuevo con otro nombre (`pawos-refugio-gui.new`) y luego renombrarlo encima del viejo con `mv` — un renombrado sí es una operación atómica que el sistema permite aunque el archivo original esté en uso; el proceso que ya está corriendo sigue usando la versión vieja en memoria hasta que se cierra, y la próxima vez que se abra ya toma el binario nuevo.

### Acceso desde Actividades de GNOME

PawOS Refugio también tiene su propio lanzador (`/usr/share/applications/pawos-refugio-gui.desktop`), así que aparece al buscar "PawOS" en Actividades y se puede anclar al dock — antes solo se podía abrir desde una terminal.

## Seguridad — estado actual

Lo que está implementado: firewall configurado (ufw), permisos de sudo restringidos por usuario (solo apagar/reiniciar, excepto `admin_refugio` que también puede usar el instalador y el respaldo), verificación de integridad de la base de donantes por checksum, y **contraseñas hasheadas** (no en texto plano) tanto en el login del CLI como en el servidor de monitoreo.

### Firewall (`ufw`)

`instalar-pawos.sh` configura `ufw` (Uncomplicated Firewall, la interfaz simplificada de Debian sobre `netfilter`/`iptables`) con estas reglas, en este orden:

```bash
ufw default deny incoming    # por defecto, rechaza toda conexion entrante
ufw default allow outgoing   # pero permite que PawOS mismo inicie conexiones salientes (ej. rclone)
ufw allow from 192.168.0.0/16 to any port 8080 proto tcp   # dashboard: solo redes locales tipo 192.168.x.x
ufw allow from 10.0.0.0/8    to any port 8080 proto tcp    # solo redes locales tipo 10.x.x.x
ufw allow from 172.16.0.0/12 to any port 8080 proto tcp    # solo redes locales tipo 172.16-31.x.x
ufw --force enable
```

La idea: por defecto Linux no bloquea nada, así que sin firewall cualquier persona en cualquier red podría llegar al puerto 8080 (el dashboard de monitoreo) o a cualquier otro puerto que termine abierto. Con estas reglas, **todo** el tráfico entrante se rechaza excepto el puerto 8080, y ese puerto **solo** responde a las tres redes privadas típicas de una LAN doméstica/institucional (`192.168.x.x`, `10.x.x.x`, `172.16.0.0`–`172.31.255.255`) — nunca desde una IP pública de Internet. El tráfico saliente se deja libre porque PawOS necesita poder conectarse afuera (por ejemplo, para subir el respaldo a Google Drive con `rclone`).

En la ISO, el hook `0100-pawos-instalar.hook.chroot` deja las reglas ya escritas y el servicio `ufw` habilitado, pero no ejecuta `ufw enable` dentro del chroot (manipular `netfilter` sin un kernel real corriendo ahí no es confiable); las reglas quedan activas solas en el primer arranque real de la ISO ya instalada.

### Cómo funciona el hasheo de contraseñas

Se usa `crypt()` de la librería estándar de C, con el algoritmo SHA-512 (los hashes que genera empiezan con el prefijo `$6$`). `crypt()` recibe la contraseña en texto plano más una "sal" (una cadena aleatoria) y devuelve un hash que incluye esa misma sal al principio, por eso no hace falta guardar la sal aparte: el hash guardado ya trae todo lo necesario para volver a verificarlo después.

**Login del CLI (tabla `usuarios`, `db.c`):**

- Al sembrar los tres usuarios por defecto (`admin_refugio`, `veterinario1`, `voluntario1`), `db_init()` genera una sal aleatoria nueva por usuario y guarda el hash resultante en la columna `password` — nunca la contraseña tal cual.
- `usuario_autenticar()` ya no compara la contraseña dentro del `SELECT` (`WHERE password=?`); en vez de eso trae el hash guardado para ese usuario, y usa `crypt(contraseña_ingresada, hash_guardado)` — `crypt()` detecta la sal dentro del propio hash guardado, recalcula, y si el resultado coincide con el hash guardado, la contraseña es correcta.
- **Migración automática:** si `db_init()` encuentra una base de datos de una instalación anterior con contraseñas todavía en texto plano (se detectan porque los hashes de `crypt()` siempre empiezan con `$` y el texto plano no), las convierte a hash en el momento, sin que el usuario tenga que hacer nada ni perder su cuenta — sigue iniciando sesión con la misma contraseña de siempre.

**Servidor de monitoreo (`servidor_monitoreo.c`):** antes la contraseña (`admin` / `pawos2026`) estaba escrita tal cual en el código fuente, visible con solo abrir el archivo. Ahora el código solo tiene guardado el *hash* de esa contraseña (`CONTRASENA_HASH`); cuando llega una petición HTTP con autenticación básica, se decodifica el usuario/contraseña en base64, y la contraseña ingresada se verifica con `crypt()` contra ese hash — la contraseña real sigue siendo `admin` / `pawos2026` para quien ya la usaba, solo cambió cómo se verifica.

Esto requiere la librería `libcrypt` (paquete `libcrypt-dev` para compilar, ya agregado a `instalar-pawos.sh` y a la lista de paquetes de la ISO) y enlazar con `-lcrypt` (ya agregado al `Makefile`, en los cuatro binarios que la necesitan: CLI, demonio de vacunas, servidor de monitoreo y GUI).

## Respaldo en la nube — estado actual

### Cómo funciona por debajo

El script `/usr/local/bin/pawos-backup-nube` (instalado por `instalar-pawos.sh`) hace el trabajo real: copia `/var/pawos/pawos.db` a Google Drive con `rclone copyto` (nombrando el archivo con fecha, hora y milisegundos, `pawos_AAAAMMDD_HHMMSS_mmm.db`, para no pisar respaldos anteriores) y sincroniza la carpeta `/var/pawos/archivos/backups` con `rclone copy`. Usa un remote de `rclone` llamado `ggdrive`, que apunta a una cuenta real de Google Drive.

Ese script lo ejecuta el servicio systemd `pawos-backup.service` (`Type=oneshot`, corre una vez y termina), disparado por el timer `pawos-backup.timer`. El servicio corre como **root**, así que la configuración de `rclone` que usa es la de la cuenta root (`/root/.config/rclone/rclone.conf`), no la del usuario que inició sesión gráficamente — importante tenerlo en cuenta si algún día hay que reconfigurar la cuenta de Drive:

```bash
sudo rclone config    # crear/editar el remote "ggdrive"
```

Confirmado funcionando en la práctica: cada corrida sube el archivo y termina en pocos segundos (`sudo journalctl -u pawos-backup.service` para ver el historial completo, con hora exacta de cada respaldo).

Como cada respaldo se sube con su propio nombre (`pawos_AAAAMMDD_HHMMSS_mmm.db`) en vez de sobreescribir siempre el mismo archivo, Google Drive termina acumulando un historial completo de versiones de la base de datos — esto es justamente lo que hace posible recuperarse de un borrado accidental: si `/var/pawos/pawos.db` se borra o se corrompe por error, no se pierde nada, porque siempre queda al menos el respaldo de la corrida anterior (automática o manual) esperando en la nube.

### Recuperarse de un borrado accidental de la base de datos

Dos scripts nuevos, instalados también por `instalar-pawos.sh`, hacen esto posible. Ambos usan `rclone lsjson` (sin ningún filtro propio de `rclone` como `--include` o `--files-only` — ver nota más abajo del porqué) y filtran/ordenan el resultado con un script corto de Python, en vez de depender de esos filtros:

- **`/usr/local/bin/pawos-listar-respaldos`** — le pregunta a Google Drive qué respaldos existen (fecha de modificación, tamaño y nombre de cada uno) y los ordena del más reciente al más antiguo. Es de solo lectura, no modifica nada.
- **`/usr/local/bin/pawos-restaurar-nube <archivo>`** — antes de tocar nada, guarda una copia de la base de datos *actual* como `/var/pawos/pawos.db.antes-de-restaurar.<fecha>` (nunca se borra sola, queda ahí por si el restore fue un error), busca en Drive el **ID único** del archivo elegido (no lo pide por nombre — ver nota abajo) y lo descarga a un archivo temporal con `rclone backend copyid`; solo si eso termina bien, lo mueve (`mv`) para reemplazar `/var/pawos/pawos.db`. Valida que el nombre de archivo tenga el formato esperado (`pawos_*.db`) antes de hacer nada, para no aceptar cualquier cosa como argumento.

Ambos aparecen integrados en la pantalla "Respaldo en la Nube" del GUI, en el bloque "Historial de respaldos" descrito abajo. **Importante:** la columna de fecha de esa tabla muestra la fecha de *modificación en Drive*, convertida a la hora local de la máquina (Drive la entrega en UTC; `pawos-listar-respaldos` hace la conversión con `datetime.astimezone()` de Python antes de imprimirla) — no es algo derivado del nombre del archivo. Dos respaldos distintos pueden mostrar la misma fecha ahí (pasó en la práctica: dos archivos con nombres distintos, subidos segundos aparte, quedaron con el mismo `ModTime` registrado por Drive). Por eso el nombre real de archivo nunca se debe reconstruir a mano a partir de la fecha visible; hay que usar siempre el que trae la fila seleccionada (o la salida de `pawos-listar-respaldos`).

Para poder reconocer un respaldo sin depender solo de la fecha, "Respaldar ahora" (ver más abajo) permite ponerle una **etiqueta** opcional (por ejemplo `antes-de-prueba`), que queda como parte del nombre del archivo (`pawos_AAAAMMDD_HHMMSS_mmm_antes-de-prueba.db`) y aparece en su propia columna en la tabla de historial.

También existe una **etiqueta por defecto** (campo "Etiqueta por defecto" en "Configuración del respaldo", guardada en `/var/pawos/backup_etiqueta_auto.txt`) que se usa automáticamente cuando no se escribe una explícita — esto cubre tanto "Respaldar ahora" dejado en blanco como el **respaldo automático del timer diario**, que corre sin nadie presente y no tiene forma de pedir una etiqueta en el momento. `pawos-backup-nube` revisa ese archivo cada vez que corre sin argumento.

> **Nota — por qué se restaura por ID y no por nombre:** a diferencia de un sistema de archivos normal, Google Drive permite que existan dos objetos con el nombre *idéntico* en la misma carpeta (no hay ninguna restricción de unicidad por nombre). Pedir un archivo por nombre con `rclone copyto` puede entonces no resolver a cuál se refiere, y fallar con `Source doesn't exist or is a directory and destination is a file`. La solución fue resolver primero el **ID** interno de Drive del archivo elegido y restaurar por ese ID (`rclone backend copyid`), que sí identifica un objeto exacto sin ambigüedad. El cambio a nombres con milisegundos (arriba) además reduce que dos respaldos terminen con el nombre exactamente igual.
>
> **Nota 2 — por qué no se usan los filtros `--include`/`--files-only` de `rclone`:** las primeras versiones de estos scripts sí los usaban, pero en pruebas reales resultaron poco confiables en este entorno: un `--include` por nombre exacto dejó pasar `archivos_backups` (la carpeta donde se sincronizan los respaldos de archivos, que vive en la misma carpeta de Drive) aunque su nombre no coincidiera — y `rclone backend copyid` rechazó ese ID con `can't copy directory`, porque apuntaba a una carpeta, no a la base de datos. Combinando `--include` con `--files-only`, en cambio, el listado no devolvía ningún resultado aunque los archivos sí existieran. La versión actual evita ambos flags: trae siempre la lista completa sin filtrar (`rclone lsjson`) y filtra en Python comparando el nombre exacto y descartando `IsDir: true`, que se comportó de forma consistente en todas las pruebas.

### Pantalla "Respaldo en la Nube" del GUI (`abrir_pantalla_respaldo` en `main_gtk.c`)

Accesible para cualquier rol, pero solo **admin_refugio** puede tocar los controles (el resto los ve deshabilitados con un tooltip "Requiere rol Administrador" — mismo patrón que las pantallas de Procesos y Memoria). Tiene cuatro secciones:

**Estado actual** — dos etiquetas de solo lectura que se llenan preguntándole a systemd (`systemctl show ... --value -p ActiveState/Result/LastTriggerUSec`), sin necesitar permisos especiales porque es una consulta, no una acción:
- "Último respaldo automático": la última vez que se disparó el timer.
- "Estado del servicio: `<ActiveState>` | Resultado: `<Result>`" — por ejemplo `inactive` / `success` cuando ya terminó bien, o `activating` mientras sigue corriendo.

**Configuración del respaldo** — dos radio buttons controlan el modo:
- **Automático** — habilita un combo box con 4 intervalos (Cada 1 día / 3 días / 1 semana / 1 mes, que internamente son 24/72/168/720 horas).
- **Manual (solo con 'Respaldar ahora')** — deshabilita el combo; el respaldo solo corre si alguien lo dispara a mano.

Debajo, el campo **"Etiqueta por defecto"** (ver arriba) — un cuadro de texto libre, sin controles de modo asociados.

Al presionar "Guardar configuración", el GUI hace dos cosas:
1. Llama (vía `sudo -n`, sin pedir contraseña) al script `/usr/local/bin/pawos-configurar-respaldo`:
   - `pawos-configurar-respaldo manual` → apaga y deshabilita `pawos-backup.timer`, borra el *override* de horario si existía.
   - `pawos-configurar-respaldo auto <horas>` → escribe un *override* de systemd en `/etc/systemd/system/pawos-backup.timer.d/override.conf` (limpia el `OnCalendar` original de "todos los días a las 11pm" y lo reemplaza por `OnUnitActiveSec=<horas>h`, es decir "cada tantas horas desde la última vez que corrió"), recarga systemd y habilita el timer.
2. Escribe el contenido del campo "Etiqueta por defecto" directo a `/var/pawos/backup_etiqueta_auto.txt` (sin `sudo`: `/var/pawos` es escribible por el grupo `pawos-refugio`, al que pertenece `admin_refugio` — ver `instalar-pawos.sh`, sección 6).

En ambos casos el resultado queda registrado en archivos que el GUI vuelve a leer cada vez que abre la pantalla, para mostrar el estado ya guardado: el modo en `/var/pawos/backup_modo.txt` (por ejemplo `manual` o `automatico:72`) y la etiqueta por defecto en `/var/pawos/backup_etiqueta_auto.txt`.

**Historial de respaldos** — una tabla (fecha local, etiqueta y tamaño) con todo lo que hay guardado en Google Drive, llenada al abrir la pantalla (y cada vez que se presiona "Actualizar estado") corriendo `pawos-listar-respaldos` y parseando su salida línea por línea. Debajo, el botón "Restaurar seleccionado":
1. Exige que haya una fila seleccionada en la tabla.
2. Muestra un diálogo de confirmación (fecha y nombre del archivo elegido), porque es una acción destructiva — reemplaza la base de datos actual.
3. Si se confirma, llama `pawos-restaurar-nube <archivo>`, que guarda la base de datos actual aparte antes de sobreescribirla (ver sección anterior).

Como con "Respaldar ahora", después de restaurar hay que cerrar y volver a abrir PawOS para que el CLI/GUI relean la base de datos ya restaurada (no la recargan sola mientras está corriendo) — importante: hay que cerrar el **programa completo**, no solo la ventana del módulo (por ejemplo "Gestión de mascotas"), porque la conexión a SQLite se abre una sola vez al arrancar y sigue apuntando al archivo viejo mientras el proceso no se reinicie.

**Botones inferiores**:
- "Actualizar estado" — vuelve a consultar systemd y refresca las dos etiquetas de arriba, y de paso recarga el historial.
- "Respaldar ahora" — pide una etiqueta opcional (ver arriba) y dispara `pawos-backup-nube [etiqueta]`.
- "Cerrar" — cierra la ventana.

### Por qué esto corre en un hilo aparte (y no directo al presionar el botón)

`pawos-listar-respaldos`, `pawos-restaurar-nube` y `pawos-backup-nube` hablan por red con Google Drive, y esa llamada puede tardar varios segundos (más si la conexión está lenta). Las primeras versiones de estas tres acciones llamaban al script directo con `system()`/`popen()` en el mismo hilo que dibuja la ventana (el hilo principal de GTK) — mientras esa llamada no terminaba, la ventana no podía redibujarse ni responder a clics, y GNOME terminaba mostrando el mensaje **"PawOS Refugio (GUI) no responde"** (confirmado en la práctica).

La solución: cada una de esas tres acciones ahora corre el comando bloqueante dentro de un hilo nuevo (`g_thread_new`), y el resultado se aplica de vuelta a la interfaz con `g_idle_add` — que es la única forma segura de tocar widgets de GTK desde fuera del hilo principal. Mientras el hilo trabaja, el botón correspondiente se deshabilita (para no disparar la misma acción dos veces) y la ventana sigue respondiendo con normalidad. Por seguridad ante el caso de que la ventana se cierre mientras un hilo sigue trabajando (por ejemplo, restaurando), cada tarea revisa una bandera (`ContextoRespaldo::vivo`) antes de tocar cualquier widget; si la ventana ya se cerró, el resultado simplemente se descarta en vez de acceder a memoria ya liberada.

Antes, "Respaldar ahora" usaba `systemctl --no-block start pawos-backup.service` (encolar la tarea en systemd y regresar de inmediato, sin esperar el resultado) como manera de no bloquear la ventana. Con el hilo en segundo plano ya no hace falta ese rodeo: ahora se llama directo a `pawos-backup-nube` (agregado a sudoers), lo que además permite mandarle la etiqueta opcional y mostrar el resultado real (éxito o error) apenas termina, en vez de tener que revisar "Actualizar estado" después. El respaldo automático (el timer diario) sigue usando el mismo servicio de systemd que antes, sin cambios.

### Permisos (sudoers)

Todo esto funciona sin pedir contraseña gracias a una regla específica en `/etc/sudoers.d/pawos-respaldo`, que solo aplica al grupo `pawos-admin` (o sea, solo `admin_refugio`) y solo para estos cinco comandos exactos:

```
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
```

(El `systemctl ... pawos-backup.service` se dejó en la lista por compatibilidad — lo sigue usando el respaldo automático — aunque "Respaldar ahora" ya no pasa por ahí, ver la sección de arriba sobre los hilos.)

Si algún día se cambian los argumentos de cualquiera de esos comandos en el código C, hay que actualizar esta línea de sudoers para que coincida exactamente, o `sudo -n` fallará en silencio (sin pedir contraseña, pero sin ejecutar nada).

> **Nota:** el hook `live-iso/hooks/0100-pawos-instalar.hook.chroot` (usado al armar la ISO) todavía no incluye `pawos-configurar-respaldo` ni su archivo de sudoers, así que tampoco tiene estos dos scripts nuevos — es una diferencia ya existente entre "instalar sobre un Debian normal" y "armar la ISO" que viene de antes de este cambio. Si se rearma la ISO, hay que portar también esa parte a mano.

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
| Seguridad básica | Completo (contraseñas hasheadas con `crypt()`/SHA-512, firewall, sudo restringido, checksum de integridad) |
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
