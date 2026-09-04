#!/usr/bin/env python3
"""
agregar-actualizacion-por-deb.py

Hace que "Buscar Actualizaciones" (boton y el aviso automatico al
iniciar) funcionen para CUALQUIER instalacion, no solo las que tienen
el codigo clonado con git en /opt/pawos-src. En vez de comparar contra
una copia de git, ahora compara la version instalada (PAWOS_VERSION)
contra la ultima publicada en GitHub Releases -- y "Actualizar ahora"
descarga e instala el .deb mas reciente con apt, en vez de intentar
compilar desde el codigo fuente.

No cambia nada de la logica de los dialogos (titulos, botones, listas
de novedades) -- solo cambia de donde sale la informacion (GitHub
Releases en vez de git) y como se instala la actualizacion (.deb en
vez de compilar).

IMPORTANTE: este script tambien copia dos archivos nuevos
(pawos-revisar-version y pawos-actualizar-deb) a la raiz del repo, y
agrega las lineas correspondientes a construir-deb.sh para que se
incluyan en el .deb la proxima vez que lo generes.

Uso: parado en la raiz del repo:
    python3 agregar-actualizacion-por-deb.py
"""

import shutil
import sys
import os

ARCHIVO_C = "src/main_gtk.c"
ARCHIVO_DEB_SCRIPT = "construir-deb.sh"

# ---------------------------------------------------------------
# 1. El bloque "comando" que arma la revision via git aparece IDENTICO
#    dos veces en el archivo (on_actualizar_clicked y
#    revisar_actualizaciones_al_iniciar) -- se reemplazan las dos por
#    la misma linea nueva, que llama al script pawos-revisar-version.
# ---------------------------------------------------------------
ANCLA_COMANDO = '''    const gchar *comando =
        "bash -c '"
        "REPO_DIR=/opt/pawos-src; RAMA=rama-Kevin; "
        "git config --global --add safe.directory \\"$REPO_DIR\\" 2>/dev/null; "
        "if [ -d \\"$REPO_DIR/.git\\" ]; then "
        "  cd \\"$REPO_DIR\\" || { echo SIN_CONEXION; exit 0; }; "
        "  git fetch origin \\"$RAMA\\" >/dev/null 2>&1 || { echo SIN_CONEXION; exit 0; }; "
        "  LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse origin/$RAMA); "
        "  if [ \\"$LOCAL\\" = \\"$REMOTE\\" ]; then echo AL_DIA; "
        "  else echo HAY_CAMBIOS; git log \\"$LOCAL..$REMOTE\\" --no-merges --pretty=format:%s; fi; "
        "else echo PRIMERA_VEZ; fi'";'''
NUEVO_COMANDO = '''    const gchar *comando =
        "/usr/local/bin/pawos-revisar-version \\"" PAWOS_VERSION "\\"";'''

# ---------------------------------------------------------------
# 2. La linea que abre el actualizador tambien aparece identica dos
#    veces -- se reemplazan las dos por el nuevo script basado en
#    .deb en vez del basado en git+compilar.
# ---------------------------------------------------------------
ANCLA_SCRIPT = '"x-terminal-emulator -e /usr/local/bin/pawos-actualizar-gui", &error_terminal);'
NUEVO_SCRIPT = '"x-terminal-emulator -e /usr/local/bin/pawos-actualizar-deb", &error_terminal);'

# ---------------------------------------------------------------
# 3. construir-deb.sh: agregar los dos scripts nuevos al paquete,
#    justo despues de donde ya se instala pawos-generar-pdf-cita.py
# ---------------------------------------------------------------
ANCLA_DEB = 'install -m 755 pawos-generar-pdf-cita.py         "$RAIZ/usr/local/bin/pawos-generar-pdf-cita.py"'
NUEVO_DEB = '''install -m 755 pawos-generar-pdf-cita.py         "$RAIZ/usr/local/bin/pawos-generar-pdf-cita.py"
install -m 755 pawos-revisar-version              "$RAIZ/usr/local/bin/pawos-revisar-version"
install -m 755 pawos-actualizar-deb               "$RAIZ/usr/local/bin/pawos-actualizar-deb"'''


def parchar_c():
    try:
        with open(ARCHIVO_C, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_C}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n_comando = contenido.count(ANCLA_COMANDO)
    if n_comando != 2:
        print(f"ERROR: el bloque 'comando' (revision via git) se encontro {n_comando} veces (se esperaban 2).")
        print("       No se cambio nada.")
        sys.exit(1)

    n_script = contenido.count(ANCLA_SCRIPT)
    if n_script != 2:
        print(f"ERROR: la linea del actualizador se encontro {n_script} veces (se esperaban 2).")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA_COMANDO, NUEVO_COMANDO)
    contenido = contenido.replace(ANCLA_SCRIPT, NUEVO_SCRIPT)

    shutil.copy(ARCHIVO_C, ARCHIVO_C + ".bak25")
    print(f"Backup creado: {ARCHIVO_C}.bak25")
    with open(ARCHIVO_C, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO_C} parchado OK: revision de actualizaciones ahora usa GitHub Releases.")


def parchar_deb_script():
    try:
        with open(ARCHIVO_DEB_SCRIPT, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO_DEB_SCRIPT}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    n = contenido.count(ANCLA_DEB)
    if n != 1:
        print(f"ERROR: la linea de instalacion de pawos-generar-pdf-cita.py se encontro {n} veces (se esperaba 1).")
        print("       No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA_DEB, NUEVO_DEB, 1)

    shutil.copy(ARCHIVO_DEB_SCRIPT, ARCHIVO_DEB_SCRIPT + ".bak2")
    print(f"Backup creado: {ARCHIVO_DEB_SCRIPT}.bak2")
    with open(ARCHIVO_DEB_SCRIPT, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO_DEB_SCRIPT} parchado OK: incluye los 2 scripts nuevos en el .deb.")


def copiar_scripts_nuevos():
    aqui = os.path.dirname(os.path.abspath(__file__))
    for nombre in ("pawos-revisar-version", "pawos-actualizar-deb"):
        origen = os.path.join(aqui, nombre)
        destino = os.path.abspath(nombre)
        if not os.path.isfile(origen) and not os.path.isfile(destino):
            print(f"ERROR: no se encontro '{nombre}' junto a este script ni en la raiz del repo.")
            sys.exit(1)
        if os.path.isfile(origen) and os.path.abspath(origen) != destino:
            shutil.copy(origen, destino)
            print(f"Copiado: {nombre}")
        else:
            print(f"Ya esta en la raiz del repo: {nombre}")
        os.chmod(destino, 0o755)
        print(f"Marcado ejecutable: {nombre}")


def main():
    copiar_scripts_nuevos()
    parchar_c()
    parchar_deb_script()

    print("")
    print("Ahora recompila y prueba:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  ./pawos-refugio-gui")
    print("")
    print("Cuando generes el proximo .deb (bash construir-deb.sh), ya va a")
    print("incluir los 2 scripts nuevos y el boton 'Actualizar' va a funcionar")
    print("para cualquier instalacion, no solo la tuya.")


if __name__ == "__main__":
    main()
