#!/usr/bin/env python3
"""
agregar-fpdf2-instalador.py

Agrega la instalacion de la libreria de Python fpdf2 (la usa
pawos-generar-pdf-cita.py para el PDF del recordatorio de citas) a
instalar-pawos.sh y al postinst del .deb (construir-deb.sh), para que
una instalacion nueva desde cero no falle al generar el PDF por falta
de esta dependencia -- como le paso a Kevin en su propia VM (fpdf2
solo estaba instalada para su usuario, no para root).

No se aborta la instalacion si pip3 falla (por ejemplo sin internet en
ese momento): se avisa con un mensaje y se puede instalar despues a
mano con el mismo comando.

Uso: parado en la raiz del repo:
    python3 agregar-fpdf2-instalador.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"

AVISO = ('pip3 install fpdf2 --break-system-packages || echo "AVISO: no se pudo instalar fpdf2. '
         'El PDF de citas no funcionara hasta correr: sudo pip3 install fpdf2 --break-system-packages"')

# ---------------------------------------------------------------
# instalar-pawos.sh
# ---------------------------------------------------------------
ANCLA_INSTALAR = """echo "=== 1. Instalando dependencias de compilacion y sistema ==="
apt-get update
apt-get install -y build-essential libncurses-dev libsqlite3-dev nasm ufw libgtk-3-dev pkg-config libcrypt-dev python3 rclone
echo "=== 2. Compilando PawOS desde el codigo fuente ===\""""
NUEVO_INSTALAR = f"""echo "=== 1. Instalando dependencias de compilacion y sistema ==="
apt-get update
apt-get install -y build-essential libncurses-dev libsqlite3-dev nasm ufw libgtk-3-dev pkg-config libcrypt-dev python3 python3-pip rclone
# fpdf2: genera el PDF del recordatorio de citas (correo/WhatsApp).
{AVISO}
echo "=== 2. Compilando PawOS desde el codigo fuente ===\""""

# ---------------------------------------------------------------
# construir-deb.sh: Depends + postinst
# ---------------------------------------------------------------
ANCLA_DEB_DEPENDS = "Depends: libgtk-3-0, libsqlite3-0, libncurses6, libcrypt1, python3, ufw, rclone"
NUEVO_DEB_DEPENDS = "Depends: libgtk-3-0, libsqlite3-0, libncurses6, libcrypt1, python3, python3-pip, ufw, rclone"

ANCLA_DEB_POSTINST = """    echo "Usuario '$USUARIO_REAL' agregado a los grupos pawos-admin y pawos-refugio."
    echo "IMPORTANTE: debe cerrar sesion y volver a entrar para que el cambio de grupo tome efecto."
fi

systemctl daemon-reload"""
NUEVO_DEB_POSTINST = f"""    echo "Usuario '$USUARIO_REAL' agregado a los grupos pawos-admin y pawos-refugio."
    echo "IMPORTANTE: debe cerrar sesion y volver a entrar para que el cambio de grupo tome efecto."
fi

# fpdf2: genera el PDF del recordatorio de citas (correo/WhatsApp).
{AVISO}

systemctl daemon-reload"""


def main():
    archivos = [
        (ARCHIVO_INSTALAR, [(ANCLA_INSTALAR, NUEVO_INSTALAR, "instalacion de dependencias")]),
        (ARCHIVO_DEB, [
            (ANCLA_DEB_DEPENDS, NUEVO_DEB_DEPENDS, "linea Depends del control"),
            (ANCLA_DEB_POSTINST, NUEVO_DEB_POSTINST, "postinst antes de systemctl daemon-reload"),
        ]),
    ]

    contenidos = {}
    for ruta, pares in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        for ancla, _nuevo, nombre in pares:
            if contenido.count(ancla) != 1:
                print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el bloque '{nombre}'.")
                print("       No se cambio nada.")
                sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, pares in archivos:
        contenido = contenidos[ruta]
        for ancla, nuevo, _nombre in pares:
            contenido = contenido.replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak4")
        print(f"Backup creado: {ruta}.bak4")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("No hace falta recompilar (son scripts bash). Verifica sintaxis:")
    print("  bash -n instalar-pawos.sh && echo OK")
    print("  bash -n construir-deb.sh && echo OK")


if __name__ == "__main__":
    main()
