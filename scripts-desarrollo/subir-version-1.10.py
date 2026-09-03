#!/usr/bin/env python3
"""
subir-version-1.10.py

Sube la version de PawOS de 1.9 a 1.10: el servicio en segundo plano
pawos-vacunas-check (corre solo, una vez al dia via systemd timer)
ahora tambien manda el recordatorio real por correo/WhatsApp cuando
la vacuna pendiente/vencida tiene un Cliente asignado, ademas de
loguear la alerta como ya hacia. Se manda una sola vez por cita.

Uso: parado en la raiz del repo:
    python3 subir-version-1.10.py
"""

import shutil
import sys

ARCHIVO = "include/version.h"

ANCLA = '#define PAWOS_VERSION "1.9"'
NUEVO = '#define PAWOS_VERSION "1.10"'


def main():
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"ERROR: no se encontro {ARCHIVO}. Corre este script desde la raiz del repo.")
        sys.exit(1)

    if contenido.count(ANCLA) != 1:
        print(f"ERROR: no se encontro (o se encontro mas de una vez) '{ANCLA}' en {ARCHIVO}.")
        print("       Puede que la version actual ya no sea 1.9. No se cambio nada.")
        sys.exit(1)

    contenido = contenido.replace(ANCLA, NUEVO, 1)

    shutil.copy(ARCHIVO, ARCHIVO + ".bak3")
    print(f"Backup creado: {ARCHIVO}.bak3")
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"{ARCHIVO} parchado OK: version 1.9 -> 1.10.")

    print("")
    print("Ahora recompila y confirma que el banner muestre 1.10:")
    print("  make clean-gui && make gui && make gui-producto")
    print("  make clean && make all")


if __name__ == "__main__":
    main()
