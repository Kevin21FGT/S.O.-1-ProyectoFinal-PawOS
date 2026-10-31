#!/usr/bin/env python3
"""
parche-readme-manual-tecnico.py

Actualiza README.md (manual tecnico) con todo lo hecho desde v1.19 hasta hoy.
NO borra lo que sigue vigente: trabaja por secciones ("## ...").

  - REEMPLAZA:  "Usuarios y roles" y "Base de datos" (estaban desactualizadas:
                SQLite local, cuentas fijas, 3 roles).
  - AGREGA al final de: "Estructura del proyecto" y "Servicios del sistema".
  - INSERTA secciones nuevas antes de "Personalización del sistema (branding)":
        Las apps de PawOS, Base de datos compartida (SQL Server),
        Portal de Clientes, Fotos de mascotas,
        Notificaciones: correo, WhatsApp y PDF, PawOS Archivos y respaldos de datos.
  - INSERTA "Historial de versiones" antes de "Requerimientos mínimos del curso".
  - Regenera el Indice (con enlaces que si funcionan).

Idempotente (marca "<!-- readme-manual-tecnico -->"), hace backup README.md.bak_readme.
No incluye contrasenas ni claves.

Uso (parado en la raiz del repo):
    python3 parche-readme-manual-tecnico.py
"""

import re
import shutil
import sys

ARCHIVO = "README.md"
MARCA = "<!-- readme-manual-tecnico -->"

# ---------------------------------------------------------------- contenido

USUARIOS = """## Usuarios y roles

PawOS maneja **dos tipos de cuentas**, con tablas y programas distintos.

### Personal del refugio (PawOS Refugio, CLI y GUI)

Se autentican contra la tabla `usuarios` de la base **SQLite local** (`/var/pawos/pawos.db`); la contraseña se guarda como *hash* (`crypt()`, SHA-512), nunca en texto plano (ver [Seguridad — estado actual](#seguridad--estado-actual)). Roles disponibles:

| Rol | Qué puede hacer |
|---|---|
| Administrador | Todo: incluye Administrar Colaboradores, Administrar Clientes, Configurar Notificaciones, Procesos, Memoria y Respaldo. |
| Veterinario | Todo lo clínico: mascotas, vacunas (registrar, editar, eliminar), adopciones y aprobar solicitudes del Portal. |
| Recepcionista | Adopciones y donantes; puede aprobar o rechazar solicitudes de adopción. |
| Rescatista | Solo Gestión de Mascotas y Alertas de Sensores. |
| Voluntario | Solo ver y registrar mascotas y vacunas; en el clic derecho de Mascotas puede ver la foto, pero no editar, cambiar estado ni eliminar. |

- La versión "producto" (`make gui-producto`, y el `.deb`) **no trae cuentas fijas**: el primer Administrador se crea con el asistente de bienvenida, y desde **Administrar Colaboradores** (solo Administrador) se crean los demás (con foto opcional en base64).
- La versión de desarrollo puede sembrar cuentas de ejemplo (`admin_refugio`, `veterinario1`, `voluntario1`); sus contraseñas iniciales están en el manual de usuario, no en este archivo.
- A nivel de Linux solo hacen falta dos grupos: `pawos-admin` (respaldos con `sudo`) y `pawos-refugio` (acceso a `/var/pawos` y a los scripts de notificación).

### Clientes (Portal de Clientes y selector de Agenda de Vacunas)

Viven en la tabla `clientes` de **SQL Server compartido** (ver [Base de datos compartida](#base-de-datos-compartida-sql-server)), con contraseña hasheada. Roles de cliente (`RolCliente` en `db.h`):

| Valor | Rol | Nota |
|---|---|---|
| 3 | Cliente | Persona normal; es el rol que recibe todo registro nuevo. |
| 0 | Jefe | Cuentas elevadas por el Administrador. |
| 1 | Supervisor | Ídem. |
| 2 | Administrador | Ídem. |

El registro público ya no deja elegir rol. El Administrador lo cambia después desde **Administrar Clientes** (clic derecho → *Cambiar rol*, o el botón de abajo). Las comparaciones de permisos usan igualdad (no `>=`), para que "Cliente" (3) nunca herede permisos de nivel alto.

"""

BASE_DATOS = """## Base de datos

PawOS usa **dos bases de datos**:

1. **SQL Server compartido (SmarterASP.NET)** para los módulos que el equipo comparte: `mascotas`, `vacunas`, `adopciones`, `solicitudes_adopcion`, `donantes`, `alertas_sensores`, `clientes` y `respaldos`. Detalle en [Base de datos compartida (SQL Server)](#base-de-datos-compartida-sql-server).
2. **SQLite local** (`/var/pawos/pawos.db`, o `./pawos.db` en pruebas) para el personal (`usuarios`), `notas_veterinario` y la configuración local. Es un solo archivo; las migraciones se hacen con `ALTER TABLE` aditivo, sin borrar datos.

Tablas principales del SQL Server:

- **mascotas**: id, nombre, especie, raza, edad, estado (`disponible` / `en_proceso` / `adoptado` / `tratamiento`), fecha de ingreso y `foto_base64`.
- **vacunas**: id, `mascota_id`, nombre de la vacuna, fecha de aplicación, fecha próxima, observaciones, `cliente_id` (el cliente a notificar) y `recordatorio_enviado`.
- **adopciones**: mascota, adoptante, contacto y fecha (al registrarla, la mascota pasa a `adoptado`).
- **solicitudes_adopcion**: pedidas desde el Portal de Clientes; estado `Pendiente` / `Aprobada` / `Rechazada`.
- **donantes**: nombre, contacto, monto y fecha.
- **clientes**: correo, contraseña (hash), nombre, teléfono, rol y `foto_base64`.
- **alertas_sensores**: alertas que manda un sensor ESP32 externo.
- **respaldos**: registro de los respaldos de datos hechos desde PawOS Archivos.

"""

APPEND_ESTRUCTURA = """
### Estructura actual del repositorio (desde v1.21)

```
S.O.-1-ProyectoFinal-PawOS/
├── Makefile                      # CLI, GUI y las apps nuevas (make gui portal-clientes archivos-gui vacunas-gui)
├── README.md                     # este manual tecnico
├── PawOS_Manual_Usuario.docx     # manual de usuario
├── instalar-pawos.sh             # instala PawOS sobre un Debian ya instalado
├── instalar-documentos.sh        # instala los scripts de PDF/correo/WhatsApp y su regla de sudoers
├── construir-deb.sh              # genera el .deb
├── pawos-actualizar-gui          # actualizador del boton "Buscar Actualizaciones"
├── pawos-notificar-cita, pawos-enviar-correo-cita, pawos-enviar-whatsapp-cita,
│   pawos-generar-pdf-cita.py, pawos-configurar-notificaciones     # recordatorios de citas
├── pawos-enviar-documento, pawos-generar-pdf-documento.py          # PDF de carnet, comprobantes y reportes
├── include/                      # headers
├── src/                          # codigo fuente (db/, auth/, archivos/, integridad/, procesos/, memoria/, ui/ ...)
├── branding/  live-build-config/  # personalizacion visual y configuracion de la ISO
├── scripts/  scripts-desarrollo/  tests/
```

Archivos fuente agregados desde v1.21:

| Archivo | Qué hace |
|---|---|
| `src/main_portal_clientes.c` | Portal de Clientes (app aparte para los clientes del refugio). |
| `src/main_archivos_gui.c` | PawOS Archivos: explorador por categorías, integridad de donantes y respaldos de datos. |
| `src/main_foto_cli.c` | `pawos-foto`: fotos de mascotas desde la terminal. |
| `src/main_vacunas_gui.c` | PawOS Vacunas GUI. |
| `src/main_monitor_gui.c` | PawOS Monitor (CPU, memoria, swap y disco con gráficas). |
"""

APPEND_SERVICIOS = """
### Servicios con la base de datos remota

`pawos-monitoreo.service` y `pawos-vacunas.service` corren como **root** y también leen la base compartida. Como la contraseña se busca en `$HOME`, necesitan:

- el archivo `/root/.pawos_db_remota` (permisos `600`) con la contraseña de la base, y
- un *drop-in* con `Environment=HOME=/root` (`/etc/systemd/system/<servicio>.service.d/home.conf`).

Sin eso, `pawos-vacunas.service` termina con `status=1`. Para ver su historial: `sudo journalctl -u pawos-vacunas`.
"""

APPS = """## Las apps de PawOS

PawOS dejó de ser un solo programa: son varias apps GTK3/C y utilidades que comparten la misma capa de datos (`src/db/db.c`).

| App | Binario | Para quién | Qué hace |
|---|---|---|---|
| PawOS Refugio (CLI) | `pawos-refugio` | Personal | Versión de texto (ncurses). |
| PawOS Refugio (GUI) | `pawos-refugio-gui` | Personal | Mascotas, Vacunas, Adopciones (con aprobación de solicitudes), Donantes, Reportes, Respaldo, Alertas, Procesos, Memoria, Colaboradores, Clientes y Notificaciones, todo en paneles embebidos. |
| PawOS Vacunas | `pawos-vacunas-gui` | Personal | CRUD de vacunas con estados a color (VENCIDA, HOY, Al día). |
| PawOS Monitor | `pawos-monitor-gui` | Personal | CPU, memoria, swap y disco en tiempo real leídos de `/proc`. No usa base de datos. |
| PawOS Archivos | `pawos-archivos-gui` | Personal | Explorador por categorías, integridad de donantes y respaldos de datos. |
| Portal de Clientes | `pawos-portal-clientes` | Clientes | Catálogo, solicitudes de adopción, mis mascotas y vacunas, donaciones, carnet y comprobantes en PDF. |
| `pawos-foto` | `pawos-foto` | Personal / pruebas | Fotos de mascotas desde la terminal. |
| `pawos-vacunas-check` | demonio | Sistema | Revisa vacunas pendientes cada día y manda los recordatorios. |

### Clic derecho en Refugio

Para no llenar la pantalla de botones, varias listas de PawOS Refugio usan **clic derecho** sobre una fila:

- **Gestión de Mascotas:** Editar datos (nombre, especie, raza, edad), Foto, Cambiar estado y Eliminar. `mascota_actualizar_datos()` en `db.c` guarda los cambios.
- **Agenda de Vacunas:** Editar y Eliminar. La tabla muestra, además del ID, el **nombre de la mascota** y el **cliente a notificar**.
- **Administrar Clientes:** Editar datos (nombre y teléfono; la contraseña y el correo no se tocan) y Cambiar rol.

Los botones de la parte de abajo se mantienen. Los roles sin permiso (por ejemplo Voluntario) ven las opciones deshabilitadas.

"""

BD_COMPARTIDA = """## Base de datos compartida (SQL Server)

Desde v1.19 los módulos principales usan un **SQL Server remoto** (SmarterASP.NET) en vez de la SQLite local, para que todo el equipo vea y edite los mismos registros.

- **Conexión:** ODBC + FreeTDS (`TDS_Version=7.4`), en `src/db/db.c` (`api_conectar` / `api_desconectar`). Las funciones conservan nombre y firma (`mascota_*`, `vacuna_*`, `adopcion_*`, `donante_*`, `alerta_*`, `cliente_*`), así que `main_gtk.c` y las pantallas no cambiaron. La conexión es persistente y se reconecta sola tras un rato de inactividad.
- **Contraseña:** nunca está en el código ni en el repo. Se lee de `~/.pawos_db_remota`. Cada usuario del equipo (y `root` para los servicios) debe tener ese archivo.
- **Servidor, base y usuario:** tienen valores por defecto en `db.c` (`API_SQL_SERVIDOR`, `API_SQL_BASE`, `API_SQL_USUARIO`) y se pueden cambiar **sin recompilar** con el archivo opcional `~/.pawos_db_config` (una clave por línea):

```
SERVIDOR=sqlXXXX.site4now.net
PUERTO=1433
BASE=db_xxxxxx_pawos
USUARIO=db_xxxxxx_pawos_admin
```

- **Dependencias:** `unixodbc`, `tdsodbc` y `freetds-bin` (el `.deb` las instala).
- **Cuenta actual:** los valores por defecto apuntan a la cuenta de paga del equipo (`sql8011.site4now.net`, base `db_acf53d_pawos`). La cuenta anterior quedó suspendida y ya no se usa.
- **Fotos:** se guardan como texto base64 en columnas `foto_base64` (mascotas y clientes).

"""

PORTAL = """## Portal de Clientes

`pawos-portal-clientes` es una app aparte, pensada para las personas que adoptan o donan, no para el personal.

- **Cuenta:** registro con foto (con editor), inicio de sesión con "ojito" para ver la contraseña, recuperar contraseña, editar perfil (nombre, teléfono, foto) y **Editar foto** sobre la foto ya guardada. Al cerrar la ventana pregunta si cerrar sesión (vuelve al login) o continuar.
- **Catálogo de mascotas** disponibles, con miniatura de la foto.
- **Solicitudes de adopción:** el cliente envía la solicitud; el personal (Veterinario, Recepcionista o Administrador) la aprueba o rechaza en *Control de Adopciones*. No se permiten dos solicitudes activas para la misma mascota.
- **Mis mascotas y vacunas:** recordatorios de vacunas del cliente (las que tienen su `cliente_id`).
- **Donaciones.**
- **Documentos en PDF:** carnet (con página "Mis mascotas" y fotos), comprobantes y reportes, descargables y enviables por correo o WhatsApp.

"""

FOTOS = """## Fotos de mascotas

Cada mascota puede tener foto. Se guarda como **JPEG de máximo 300 px en base64** en `mascotas.foto_base64` (SQL Server).

- **Refugio GUI:** al registrar una mascota o con clic derecho → *Foto*. El editor permite girar, voltear, ajustar brillo y contraste, hacer zoom y encuadre, y capturar con cámara (por ejemplo DroidCam).
- **Portal de Clientes:** catálogo con miniaturas, y fotos de las mascotas en el carnet y los comprobantes.
- **PawOS Archivos:** exporta las fotos de las mascotas a archivos `.jpg` y las incluye en el respaldo de datos.
- **Terminal:** `pawos-foto`:

```
pawos-foto listar
pawos-foto poner <id> <imagen> [--cuadrada]
pawos-foto ver <id> <salida.jpg>
pawos-foto quitar <id>
```

"""

NOTIFICACIONES = """## Notificaciones: correo, WhatsApp y PDF

PawOS manda avisos por **correo (Gmail)** y **WhatsApp (Green API)**, casi siempre con un PDF adjunto.

| Aviso | Cuándo | Canales |
|---|---|---|
| Recordatorio de cita | Al registrar una vacuna con *Cliente a notificar* (con confirmación), y automáticamente cada día a las 8:00 por `pawos-vacunas-check` si la vacuna está pendiente o vencida | Correo y WhatsApp, con PDF |
| Solicitud aprobada | Al aprobarla en Control de Adopciones | Correo y WhatsApp, con PDF del comprobante y foto de la mascota |
| Solicitud rechazada | Al rechazarla | Solo correo, con el indicador de estado |

Piezas:

- `pawos-generar-pdf-cita.py` y `pawos-generar-pdf-documento.py` (fpdf2 y segno para el QR) arman los PDF: citas, carnet, comprobantes y tablas.
- `pawos-enviar-correo-cita`, `pawos-enviar-whatsapp-cita` y `pawos-enviar-documento` hacen el envío.
- `pawos-notificar-cita` (recordatorios) y `pawos-notificar-solicitud` (solicitudes) orquestan todo. Esta última registra cada intento en `~/.pawos_notificaciones.log`.
- **Credenciales:** el Administrador las guarda desde *Configurar Notificaciones*, que llama por `sudo` a `pawos-configurar-notificaciones`, el único con permiso de escribir `/etc/pawos/notificaciones.conf` (`root`, permisos `600`). El formulario **no muestra los valores guardados**: guardarlo con campos vacíos borraría la configuración.
- **Permisos:** una regla de sudoers (`/etc/sudoers.d/pawos-documentos`, grupo `pawos-refugio`) permite ejecutar solo los scripts de envío. Se instala con `sudo bash instalar-documentos.sh`.
- **Teléfonos:** si el número tiene 8 dígitos se le antepone el código de Guatemala (`502`) antes de enviar por WhatsApp.

"""

ARCHIVOS = """## PawOS Archivos y respaldos de datos

`pawos-archivos-gui` es el explorador de archivos del refugio.

- **Categorías:** mascotas, vacunas, adopciones, donantes, reportes y backups. Soporta carpetas, arrastrar y soltar, selección múltiple y clic derecho.
- **Integridad de donantes:** verifica el checksum (rutina en Ensamblador, ver [Integridad de datos](#integridad-de-datos-integridadc--checksumasm)).
- **Respaldo de datos:** "Respaldar datos ahora" exporta las tablas del SQL Server a **CSV** locales (con las fotos de las mascotas) y registra el respaldo en la tabla `respaldos`, con validación en la nube.
- **Respaldo de la base remota:** además, desde el panel de SmarterASP se puede generar un `.bak`; conviene guardar una copia **fuera de la máquina virtual**.

"""

HISTORIAL = """## Historial de versiones

Resumen tomado de los commits de `rama-Combinada`.

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 – 1.1 | 17–18 ago | Número de versión visible; reportes por categoría con historial, "Guardar como" `.txt`/`.pdf` y PDF con diseño; fondo y avatares de usuario. |
| 1.2 – 1.3 | 27–30 ago | Diálogo de novedades al buscar actualizaciones; mensajes distintos en el login de clientes. |
| 1.4 | 31 ago | Asistente de bienvenida, Administrar Colaboradores, roles Rescatista y Recepcionista, correcciones de memoria. |
| 1.5 – 1.7 | 31 ago | Correcciones del actualizador (permisos, `safe.directory`, sudoers sin contraseña). |
| 1.8 | 1 sep | Recordatorio de citas (PDF + correo + WhatsApp), teléfono en cliente, selector de cliente en vacunas, Configurar Notificaciones y Administrar Clientes. |
| 1.9 – 1.11 | 2–3 sep | Scripts de recordatorio en instalador y `.deb`; recordatorios automáticos con `pawos-vacunas-check`; instalación automática de fpdf2. |
| 1.13 – 1.17 | 3–5 sep | Mejoras de interfaz, aviso de actualizaciones y correcciones del instalador. |
| 1.18 | 10 sep | 11 de 12 módulos pasan a paneles embebidos; corrección de maximizar. |
| 1.19 | 12 sep | Gestión de Mascotas en SQL Server compartido (ODBC/FreeTDS). |
| 1.20 | 12 sep | Vacunas, adopciones, donantes y alertas también en SQL Server; conexión persistente; cursor de carga. |
| 1.21 | 2 oct | Nuevas apps: Vacunas GUI, Monitor y Portal de Clientes; Clientes migrado a SQL Server. |
| Sin versión asignada | 8–27 oct | PawOS Archivos y respaldos de datos; Portal ampliado (catálogo, solicitudes, donaciones, recuperar contraseña, carnet y comprobantes en PDF); fotos de mascotas con editor y cámara; aprobación de solicitudes; avisos de solicitud con PDF; rol Cliente; configuración de la base por archivo; `pawos-foto`; cambio a la cuenta de paga; clic derecho en Mascotas, Vacunas y Clientes; columnas Mascota y Cliente en vacunas; Editar foto en el Portal; corrección del prefijo 502 en WhatsApp de citas. |

**Pendiente:** `.deb`, número de versión, etiqueta y release con todo lo anterior, y el diseño final de correos y PDF.

"""

REEMPLAZOS = {
    "## Usuarios y roles": USUARIOS,
    "## Base de datos": BASE_DATOS,
}
AGREGAR_AL_FINAL = {
    "## Estructura del proyecto": APPEND_ESTRUCTURA,
    "## Servicios del sistema (systemd)": APPEND_SERVICIOS,
}
REPORTES = """## Reportes

El módulo **Reportes** de PawOS Refugio genera un resumen del refugio como archivo.

- **Por categoría:** se elige qué incluir (mascotas, vacunas, adopciones, donantes, etc.).
- **Historial de reportes:** cada reporte generado queda guardado y se puede volver a abrir (carpeta `reportes` de PawOS Archivos).
- **Guardar como:** `.txt` o `.pdf`, con un diálogo para elegir dónde guardar. El PDF tiene diseño profesional (encabezado de marca, tablas y resumen).
- **Pendiente:** descargar o enviar el reporte por correo y WhatsApp desde la propia pantalla (hoy eso lo hacen el Portal de Clientes y las notificaciones).

"""

PANELES = """## Interfaz de PawOS Refugio: paneles embebidos

Desde v1.18 los módulos ya no abren ventanas emergentes encima: se dibujan en el **área dinámica** de la ventana principal, a la derecha del menú lateral.

- **11 de 12 módulos** son paneles: Mascotas, Vacunas, Adopciones, Donantes, Reportes, Procesos, Memoria, Respaldo, Alertas, Colaboradores y Clientes. **Configurar Notificaciones** sigue como diálogo modal a propósito, porque es un formulario y no un listado.
- Cada panel se construye con `abrir_pantalla_*` y se muestra con `mostrar_en_panel()`, que destruye el panel anterior. Su contexto se guarda con `g_object_set_data_full()`, así que se libera solo cuando el panel se reemplaza, sin depender de cerrar ninguna ventana.
- El botón **Cerrar** de cada panel vuelve a la tarjeta de bienvenida.
- Menú lateral organizado en secciones: *Atención al refugio*, *Gestión y administración*, *Sistema* y *Cuenta* (Buscar Actualizaciones, Acerca de, Salir).
- **Maximizar y redimensionar:** se corrigió el botón de maximizar (tipo de ventana y comparación contra el tamaño real del monitor).
- **Rol y permisos:** cada módulo se muestra u oculta con `modulo_permitido(rol, indice)`; las acciones sin permiso aparecen deshabilitadas, no ocultas.
- **Pendientes de diseño:** evitar el scroll del menú lateral y el espacio vacío al maximizar.

"""

COLABORADORES = """## Administrar Colaboradores y asistente de bienvenida

- **Asistente de bienvenida:** en la versión "producto" (`make gui-producto` y el `.deb`) no hay cuentas fijas. La primera vez, el asistente crea al primer Administrador.
- **Administrar Colaboradores** (solo Administrador): crea Veterinario, Voluntario, Rescatista, Recepcionista u otro Administrador, con foto opcional guardada en base64.
- **Administrar Clientes** (solo Administrador): lista las cuentas del Portal, cambia su rol y edita nombre y teléfono (clic derecho).
- Las contraseñas del personal y de los clientes se guardan hasheadas (ver [Seguridad — estado actual](#seguridad--estado-actual)).

"""

MONITOR = """## Monitoreo del sistema

Hay dos piezas distintas:

- **PawOS Monitor** (`pawos-monitor-gui`): app GTK local con CPU, memoria, swap y disco en tiempo real, con gráficas de historial (líneas y área degradada). Lee `/proc` directamente y no depende de la base de datos.
- **Servidor de monitoreo** (`pawos-monitoreo`, puerto 8080): dashboard web con autenticación básica y el endpoint `POST /api/alerta` para el sensor ESP32 (ver [Módulos del programa](#módulos-del-programa)).

"""

PARTES = {
    "## De cero a un sistema operativo funcionando":
        "# Parte 1 — Visión general, requisitos y compilación",
    "## Usuarios y roles":
        "# Parte 2 — Usuarios, datos y módulos base",
    "## Las apps de PawOS":
        "# Parte 3 — Apps y funciones del refugio",
    "## Personalización del sistema (branding)":
        "# Parte 4 — Personalización, instalación y distribución",
    "## Servicios del sistema (systemd)":
        "# Parte 5 — Operación, seguridad y respaldos",
    "## Historial de versiones":
        "# Parte 6 — Historial y checklist del curso",
}

INSERTAR_ANTES = {
    "## Módulos del programa": [BD_COMPARTIDA],
    "## Personalización del sistema (branding)": [APPS, PANELES, REPORTES, PORTAL, FOTOS,
                                                  NOTIFICACIONES, ARCHIVOS, COLABORADORES, MONITOR],
    "## Requerimientos mínimos del curso — checklist": [HISTORIAL],
}


def dividir_secciones(texto):
    """Devuelve [(titulo_o_None, cuerpo_con_titulo)] separando por lineas '## '
    fuera de bloques de codigo."""
    secciones = []
    actual_titulo = None
    actual = []
    en_codigo = False
    for linea in texto.splitlines(keepends=True):
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo and linea.startswith("## "):
            secciones.append((actual_titulo, "".join(actual)))
            actual_titulo = linea.rstrip("\n").rstrip()
            actual = [linea]
        else:
            actual.append(linea)
    secciones.append((actual_titulo, "".join(actual)))
    return secciones


def ancla(titulo):
    s = titulo[3:].strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def construir_indice(titulos):
    lineas = ["## Índice", ""]
    for t in titulos:
        if t == "## Índice":
            continue
        if t.startswith("# "):
            lineas.append("")
            lineas.append(f"**{t[2:].strip()}**")
            lineas.append("")
            continue
        lineas.append(f"- [{t[3:].strip()}](#{ancla(t)})")
    return "\n".join(lineas) + "\n\n"


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre esto desde la raiz del repo.")
        sys.exit(1)

    if MARCA in contenido:
        print("Este parche ya fue aplicado. No se cambio nada.")
        sys.exit(0)

    secciones = dividir_secciones(contenido)
    titulos = [t for t, _ in secciones if t]

    necesarios = (list(REEMPLAZOS) + list(AGREGAR_AL_FINAL) + list(INSERTAR_ANTES) + ["## Índice"])
    for t in necesarios:
        n = titulos.count(t)
        if n != 1:
            print(f"ERROR: la seccion '{t}' aparece {n} veces (debe ser 1). No se cambio nada.")
            sys.exit(1)

    def con_parte(lista, titulo, cuerpo):
        """Agrega el encabezado de 'Parte N' antes del primer bloque de cada parte."""
        if titulo in PARTES:
            lista.append((PARTES[titulo], PARTES[titulo] + "\n\n"))
        lista.append((titulo, cuerpo))

    nuevas = []
    for titulo, cuerpo in secciones:
        if titulo in INSERTAR_ANTES:
            for bloque in INSERTAR_ANTES[titulo]:
                con_parte(nuevas, bloque.splitlines()[0].rstrip(), bloque)
        if titulo in REEMPLAZOS:
            cuerpo = REEMPLAZOS[titulo]
        elif titulo in AGREGAR_AL_FINAL:
            cuerpo = cuerpo.rstrip("\n") + "\n" + AGREGAR_AL_FINAL[titulo] + "\n"
        con_parte(nuevas, titulo, cuerpo)

    titulos_finales = [t for t, _ in nuevas if t]
    salida = []
    for titulo, cuerpo in nuevas:
        if titulo == "## Índice":
            salida.append(construir_indice(titulos_finales))
        else:
            salida.append(cuerpo)
    texto = "".join(salida)
    texto = texto.rstrip("\n") + "\n\n" + MARCA + "\n"

    shutil.copy(ARCHIVO, ARCHIVO + ".bak_readme")
    print(f"Backup: {ARCHIVO}.bak_readme")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"{ARCHIVO} actualizado: {len(titulos_finales)} secciones (antes {len(titulos)}).")
    print("Revisalo con:  git diff --stat README.md   y abrelo en GitHub para ver el formato.")


if __name__ == "__main__":
    main()
