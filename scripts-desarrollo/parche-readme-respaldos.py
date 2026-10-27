#!/usr/bin/env python3
"""
parche-readme-respaldos.py   (despues de parche-readme-manual-tecnico.py)

README.md: reemplaza la seccion "PawOS Archivos y respaldos de datos" por una
explicacion completa de los dos botones de respaldo:

    Respaldar carpeta       (copia ARCHIVOS de una carpeta)
    Respaldar datos ahora   (respalda la BASE DE DATOS, fotos y usuarios)

Idempotente (marca "<!-- readme-respaldos -->"), backup README.md.bak_respaldos.

Uso (parado en la raiz del repo):
    python3 parche-readme-respaldos.py
"""

import shutil
import sys

ARCHIVO = "README.md"
MARCA = "<!-- readme-respaldos -->"
TITULO = "## PawOS Archivos y respaldos de datos"

NUEVA = """## PawOS Archivos y respaldos de datos

`pawos-archivos-gui` (`src/main_archivos_gui.c`) es el explorador de los archivos del refugio. Los organiza por categorías dentro de `/var/pawos/archivos`: mascotas, vacunas, adopciones, donantes, reportes y backups. Soporta carpetas, arrastrar y soltar, selección múltiple y clic derecho. También verifica la integridad de los donantes (ver [Integridad de datos](#integridad-de-datos-integridadc--checksumasm)).

Tiene **dos botones de respaldo** que hacen cosas distintas:

| | **Respaldar carpeta** | **Respaldar datos ahora** |
|---|---|---|
| Qué respalda | **Archivos** de una carpeta (fotos, PDF, documentos, subcarpetas) | **Datos de la base** (tablas en CSV), fotos de las mascotas y la base local de usuarios |
| Lee SQL Server | No | Sí |
| Sube algo a SmarterASP | No | Sí (una fila por tabla en la tabla `respaldos`) |
| Dónde guarda | `Backups/<nombre>/<carpeta>` | `Backups/<nombre>/` |
| Función | `on_respaldar_carpeta_clicked()` | `on_respaldar_clicked()` |
| Otro acceso | — | Clic derecho → *Respaldar datos ahora* |

<!-- readme-respaldos -->

### Respaldar carpeta (archivos)

Copia una carpeta completa, tal cual está, a `Backups/<nombre>/<carpeta>`. Es una copia de archivos en la misma computadora; no toca la base de datos.

**Qué carpeta se respalda:**

- Si **no hay nada marcado** en la lista, la carpeta que está abierta en ese momento.
- Si hay **una sola carpeta marcada**, esa carpeta.
- Si hay archivos sueltos o varias cosas marcadas, no respalda y avisa que se marque una sola carpeta (o que se quite la selección con un clic en un espacio vacío).
- En la categoría **Backups** no funciona ("Backups ya guarda tus respaldos").

**Cómo funciona:**

1. Pide el nombre de la carpeta del respaldo (`pedir_carpeta_respaldo()`), con la fecha y hora por defecto, por ejemplo `mascotas_2026-10-27_09-59`. Valida que no esté vacío, que no contenga `/` ni `\\`, que no sea demasiado largo y que **no exista ya** en `Backups`. Aquí no se consulta la nube.
2. Copia de forma recursiva (`copiar_recursivo()`): crea las subcarpetas y copia cada archivo con `g_file_copy`.
3. Muestra el resultado: carpeta, destino, cantidad de archivos copiados con su tamaño, y archivos con error.

Sirve para proteger lo que se guardó como archivos: fotos exportadas, documentos y reportes.

### Respaldar datos ahora (base de datos)

Respalda la **información del refugio**. Al pulsarlo abre primero una lista con casillas para **elegir qué respaldar** (todo viene marcado por defecto):

- las 7 tablas de SQL Server: `mascotas`, `vacunas`, `adopciones`, `donantes`, `alertas_sensores`, `clientes` y `notas_veterinario`;
- las **fotos de las mascotas** (archivos `.jpg`);
- la **base local de usuarios del personal** (SQLite).

Se puede respaldar una sola tabla. Si se marca una sola cosa, el nombre sugerido la incluye (por ejemplo `Respaldo_mascotas_2026-10-27_10-30`).

**Cómo funciona (`on_respaldar_clicked()`):**

1. **Elige el nombre.** Por defecto `Respaldo_AAAA-MM-DD_HH-MM`. Revisa que no exista en `Backups` y consulta si ya existe en SmarterASP (`respaldo_existe_nombre()`). Si existe en la nube, ofrece **reemplazar** (borra el anterior con `respaldo_borrar_nombre()` y sube el nuevo, para no duplicar) o elegir otro nombre. Si hay una carpeta de Backups marcada que ya está en la nube, pregunta si **actualizar ese respaldo** o crear uno nuevo.
2. **Lee las tablas elegidas** de SQL Server (`TABLAS_RESPALDO[]`, cada una con su función `csv_*`). Si alguna falla, **no se guarda nada a medias** y se muestra qué tabla falló.
3. **Guarda cada tabla** como `Backups/<nombre>/<tabla>.csv` y la registra en la tabla `respaldos` de SmarterASP con `respaldo_guardar()` (columnas `fecha`, `tabla`, `contenido`).
4. **Exporta las fotos** de las mascotas a `Backups/<nombre>/fotos_mascotas/<id>_<nombre>.jpg` (`exportar_fotos_mascotas()`, decodificando el base64 de `mascotas.foto_base64`).
5. **Copia la base local de usuarios** (`archivos_respaldar_bd_auto()`).
6. **Resumen:** cuántos CSV se guardaron, cuántos se copiaron a SmarterASP, cuántas fotos y si se copió el SQLite. Solo informa lo que se eligió.

El CSV de `clientes` incluye correo, nombre, teléfono y rol, **no las contraseñas** ni las fotos.

### Qué se guarda y dónde

| Qué | Dónde |
|---|---|
| CSV de cada tabla | `/var/pawos/archivos/backups/<nombre>/<tabla>.csv` |
| Fotos de mascotas | `/var/pawos/archivos/backups/<nombre>/fotos_mascotas/` |
| Copia de las tablas en SQL Server | tabla `respaldos` de la base compartida |
| Copia de una carpeta de archivos | `/var/pawos/archivos/backups/<nombre>/<carpeta>/` |

### Límites y recomendaciones

- La copia en la tabla `respaldos` está **en la misma base de datos** que los datos vivos: no protege si se pierde la base entera. Para eso hay que guardar también el `.bak` que se genera desde el panel de SmarterASP y los CSV **fuera de la máquina virtual**.
- El respaldo en Google Drive de la base SQLite local es otro mecanismo, independiente de este (ver [Respaldo en la nube](#respaldo-en-la-nube--estado-actual)).

"""


def dividir(texto):
    secciones, titulo, actual, en_codigo = [], None, [], False
    for linea in texto.splitlines(keepends=True):
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        if not en_codigo and linea.startswith("## "):
            secciones.append((titulo, "".join(actual)))
            titulo = linea.rstrip()
            actual = [linea]
        else:
            actual.append(linea)
    secciones.append((titulo, "".join(actual)))
    return secciones


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

    secciones = dividir(contenido)
    titulos = [t for t, _ in secciones]
    if titulos.count(TITULO) != 1:
        print(f"ERROR: la seccion '{TITULO}' aparece {titulos.count(TITULO)} veces (debe ser 1). No se cambio nada.")
        sys.exit(1)

    salida = "".join(NUEVA if t == TITULO else cuerpo for t, cuerpo in secciones)
    shutil.copy(ARCHIVO, ARCHIVO + ".bak_respaldos")
    print(f"Backup: {ARCHIVO}.bak_respaldos")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(salida)
    print(f"{ARCHIVO} actualizado: seccion de respaldos reescrita.")


if __name__ == "__main__":
    main()
