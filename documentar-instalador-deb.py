#!/usr/bin/env python3
"""
documentar-instalador-deb.py

Agrega al README.md una seccion nueva documentando el instalador .deb
(construir-deb.sh + pawos-refugio_<version>_amd64.deb), la forma mas
rapida de instalar PawOS Refugio en la maquina de un companero de
equipo sin tener que compilar nada ahi.

Uso: parado en la raiz del repo:
    python3 documentar-instalador-deb.py

Hace backup (.bak) antes de tocar nada, y aborta sin cambiar nada si
el texto esperado no aparece exactamente como se espera.
"""

import shutil
import sys

ARCHIVO = "README.md"

ANCLA_INDICE = """- [Instalar PawOS sobre un Debian ya instalado](#instalar-pawos-sobre-un-debian-ya-instalado)
- [Construir la ISO instalable](#construir-la-iso-instalable)"""

NUEVO_INDICE = """- [Instalar PawOS sobre un Debian ya instalado](#instalar-pawos-sobre-un-debian-ya-instalado)
- [Instalar desde el paquete .deb (companeros de equipo)](#instalar-desde-el-paquete-deb-companeros-de-equipo)
- [Construir la ISO instalable](#construir-la-iso-instalable)"""

ANCLA_SECCION = """Este script (pensado para correr sobre una instalación normal de Debian 13) hace todo de una vez: instala las librerías necesarias, compila el CLI y el GUI, instala los binarios en `/usr/local/bin`, crea los tres usuarios y sus grupos, crea `/var/pawos` con los permisos correctos, instala y habilita los servicios de systemd, configura el firewall, y crea los accesos directos de escritorio.

## Construir la ISO instalable"""

NUEVO_SECCION = """Este script (pensado para correr sobre una instalación normal de Debian 13) hace todo de una vez: instala las librerías necesarias, compila el CLI y el GUI, instala los binarios en `/usr/local/bin`, crea los tres usuarios y sus grupos, crea `/var/pawos` con los permisos correctos, instala y habilita los servicios de systemd, configura el firewall, y crea los accesos directos de escritorio.

## Instalar desde el paquete .deb (compañeros de equipo)

Para repartir PawOS Refugio entre el equipo sin que cada quien tenga que compilar el código en su propia máquina, existe una segunda forma de instalar, más parecida a un instalador de Windows: un paquete `.deb` ya compilado.

Diferencia con `instalar-pawos.sh`: ese script **compila** en la máquina de destino (necesita el código fuente y el compilador ahí). El paquete `.deb` en cambio se compila **una sola vez**, en la máquina de quien lo genera, y el resultado ya trae los binarios listos — quien lo instala no necesita el código fuente ni ningún compilador.

### Generar el paquete

Parado en la raíz del repo, con todo el código actualizado:

```bash
bash construir-deb.sh
```

Esto compila el CLI y el GUI, arma la estructura de un paquete Debian (binarios, accesos directos, servicios de systemd, reglas de sudo) y genera un archivo `pawos-refugio_<version>_amd64.deb` en la carpeta actual. La versión se toma automáticamente de `include/version.h`.

### Instalar el paquete

En la máquina del compañero (su propia VM de Debian 13), con el archivo `.deb` ya copiado ahí (por USB, Drive, etc.):

```bash
sudo apt install ./pawos-refugio_<version>_amd64.deb
```

`apt` resuelve automáticamente las dependencias que falten (GTK3, SQLite, ncurses, rclone, etc.). Al terminar, hay que cerrar sesión y volver a entrar para que los grupos nuevos de Linux queden activos (ver siguiente punto).

### Diferencia importante con `instalar-pawos.sh`: no crea cuentas fijas

Como el login de PawOS Refugio (tanto CLI como GUI) ya no depende de cuentas de Linux — se autentica contra la tabla `usuarios`/`clientes` de la base de datos, ver [Usuarios y roles](#usuarios-y-roles) — el paquete `.deb` **no** crea las cuentas fijas `admin_refugio`/`veterinario1`/`voluntario1` con contraseña en el código. En vez de eso, el script `postinst` del paquete agrega automáticamente a quien lo instaló (el usuario real detrás de `sudo`) a los grupos `pawos-admin` y `pawos-refugio`, que es lo único que sigue haciendo falta a nivel de Linux: el respaldo en la nube usa `sudo` gateado por el grupo `pawos-admin` (ver [Permisos (sudoers)](#respaldo-en-la-nube--estado-actual)), y el acceso de lectura/escritura a `/var/pawos` requiere estar en el grupo `pawos-refugio`.

## Construir la ISO instalable"""


def aplicar(contenido, ancla, nuevo, nombre):
    if contenido.count(ancla) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
        print("       Puede que el README.md ya haya sido modificado. No se cambio nada.")
        sys.exit(1)
    return contenido.replace(ancla, nuevo, 1)


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    contenido = aplicar(contenido, ANCLA_INDICE, NUEVO_INDICE, "indice")
    contenido = aplicar(contenido, ANCLA_SECCION, NUEVO_SECCION, "seccion de instalacion")

    shutil.copy(ARCHIVO, ARCHIVO + ".bak2")
    print(f"Backup creado: {ARCHIVO}.bak2")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"{ARCHIVO} actualizado OK.")


if __name__ == "__main__":
    main()
