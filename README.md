# PawOS - Programa de Gestion del Refugio

Aplicacion en C (ncurses + SQLite) para la causa Proteccion Animal del
proyecto final de Sistemas Operativos I.

## Que hace

Menu principal con 5 modulos:
- Gestion de Mascotas (registrar, listar, cambiar estado, eliminar)
- Agenda de Vacunas (registrar, ver todas, ver pendientes/vencidas)
- Control de Adopciones (registrar adopcion -> marca la mascota como adoptada)
- Base de Donantes (registrar, listar, total recaudado)
- Reportes (genera un .txt con el resumen del refugio)

## Roles

El programa NO pide usuario/contrasena (eso ya lo hace el login grafico
de PawOS, LightDM, antes de abrir la sesion). Al iniciar, detecta con
qué usuario de Linux se ejecuta y a qué grupo pertenece:

- `pawos-admin`        -> Administrador: acceso total.
- `pawos-veterinario`  -> Veterinario: todo excepto (mismo que admin en esta version).
- `pawos-voluntario`   -> Voluntario: solo puede ver/registrar mascotas y
  ver vacunas; no accede a Donantes ni Reportes, ni elimina/cambia estados.

Los grupos y usuarios de ejemplo se crean con `scripts/crear_usuarios.sh`
(ejecutar como root dentro de la VM o del hook de live-build).

## Compilar (en su VM Debian/Ubuntu)

```bash
sudo apt install build-essential libncurses-dev libsqlite3-dev
cd pawos-app
make
```

## Ejecutar

```bash
sudo mkdir -p /var/pawos/reportes
sudo chown $USER /var/pawos -R
./pawos-refugio
```

Si no existe `/var/pawos` (por ejemplo probando en su propia laptop, fuera
de la ISO), el programa usa automaticamente `./pawos.db` en la carpeta
actual, para que puedan probarlo sin tener montado todo PawOS.

## Integrarlo a la ISO (live-build)

1. Copien el binario ya compilado `pawos-refugio` a
   `config/includes.chroot/usr/local/bin/pawos-refugio` en su repo de
   live-build (o compilen dentro de un hook).
2. Copien `scripts/crear_usuarios.sh` a `config/hooks/normal/` (renombrado
   con prefijo numerico, ej. `0100-crear-usuarios.hook.chroot`) para que
   se ejecute al construir la imagen.
3. Hagan que la sesion grafica (autostart tras el login de LightDM)
   lance `pawos-refugio` en una terminal a pantalla completa.

## Estructura

```
pawos-app/
├── Makefile
├── include/       (headers: db.h, ui.h, auth.h, pantallas.h)
├── src/           (db.c, ui.c, auth.c, pantallas.c, main.c)
├── scripts/       (crear_usuarios.sh)
└── data/          (aqui puede vivir pawos.db durante pruebas locales)
```

## Estado de pruebas

La capa de datos (`db.c`) fue probada de forma automatica: alta de
mascotas, vacunas pendientes, adopcion (transaccion que marca la mascota
como adoptada), donantes y generacion de reporte -- todo paso
correctamente. La interfaz ncurses se compilo y enlazo sin errores;
pruebenla de forma interactiva en su VM (necesita una terminal real).
