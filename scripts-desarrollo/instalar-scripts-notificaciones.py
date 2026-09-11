#!/usr/bin/env python3
"""
instalar-scripts-notificaciones.py

Agrega la copia de los 5 scripts de recordatorio de citas a
instalar-pawos.sh y construir-deb.sh, para que una instalacion nueva
desde cero (o un .deb reconstruido) los deje listos en
/usr/local/bin, igual que pawos-refugio-gui y los demas binarios.
Hasta ahora solo estaban en git como archivos sueltos -- no se
copiaban automaticamente en una instalacion nueva.

Scripts que se agregan:
  - pawos-notificar-cita
  - pawos-configurar-notificaciones
  - pawos-enviar-correo-cita
  - pawos-enviar-whatsapp-cita
  - pawos-generar-pdf-cita.py

No toca las reglas de sudoers (ya estan en
/etc/sudoers.d/pawos-notificaciones desde
agregar-sudoers-notificaciones.py) ni nada mas de lo ya construido.

Uso: parado en la raiz del repo:
    python3 instalar-scripts-notificaciones.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"

# ---------------------------------------------------------------
# instalar-pawos.sh
# ---------------------------------------------------------------
ANCLA_INSTALAR = """install -m 755 "$BINDIR/pawos-refugio"        /usr/local/bin/pawos-refugio
install -m 755 "$BINDIR/pawos-vacunas-check"  /usr/local/bin/pawos-vacunas-check
install -m 755 "$BINDIR/pawos-monitoreo"      /usr/local/bin/pawos-monitoreo
install -m 755 "$BINDIR/pawos-refugio-gui"    /usr/local/bin/pawos-refugio-gui
echo "=== 4. Creando script de respaldo a la nube (rclone) ==="""
NUEVO_INSTALAR = """install -m 755 "$BINDIR/pawos-refugio"        /usr/local/bin/pawos-refugio
install -m 755 "$BINDIR/pawos-vacunas-check"  /usr/local/bin/pawos-vacunas-check
install -m 755 "$BINDIR/pawos-monitoreo"      /usr/local/bin/pawos-monitoreo
install -m 755 "$BINDIR/pawos-refugio-gui"    /usr/local/bin/pawos-refugio-gui

echo "=== 3b. Copiando scripts de recordatorio de citas (correo/WhatsApp) ==="
install -m 755 "$BINDIR/pawos-notificar-cita"               /usr/local/bin/pawos-notificar-cita
install -m 755 "$BINDIR/pawos-configurar-notificaciones"    /usr/local/bin/pawos-configurar-notificaciones
install -m 755 "$BINDIR/pawos-enviar-correo-cita"            /usr/local/bin/pawos-enviar-correo-cita
install -m 755 "$BINDIR/pawos-enviar-whatsapp-cita"          /usr/local/bin/pawos-enviar-whatsapp-cita
install -m 755 "$BINDIR/pawos-generar-pdf-cita.py"           /usr/local/bin/pawos-generar-pdf-cita.py

echo "=== 4. Creando script de respaldo a la nube (rclone) ==="""

# ---------------------------------------------------------------
# construir-deb.sh
# ---------------------------------------------------------------
ANCLA_DEB = """install -m 755 pawos-refugio        "$RAIZ/usr/local/bin/pawos-refugio"
install -m 755 pawos-vacunas-check  "$RAIZ/usr/local/bin/pawos-vacunas-check"
install -m 755 pawos-monitoreo      "$RAIZ/usr/local/bin/pawos-monitoreo"
install -m 755 pawos-refugio-gui    "$RAIZ/usr/local/bin/pawos-refugio-gui"
[ -f branding/pawos-icon.png ] && install -m 644 branding/pawos-icon.png "$RAIZ/usr/share/icons/pawos-icon.png\""""
NUEVO_DEB = """install -m 755 pawos-refugio        "$RAIZ/usr/local/bin/pawos-refugio"
install -m 755 pawos-vacunas-check  "$RAIZ/usr/local/bin/pawos-vacunas-check"
install -m 755 pawos-monitoreo      "$RAIZ/usr/local/bin/pawos-monitoreo"
install -m 755 pawos-refugio-gui    "$RAIZ/usr/local/bin/pawos-refugio-gui"

install -m 755 pawos-notificar-cita              "$RAIZ/usr/local/bin/pawos-notificar-cita"
install -m 755 pawos-configurar-notificaciones   "$RAIZ/usr/local/bin/pawos-configurar-notificaciones"
install -m 755 pawos-enviar-correo-cita          "$RAIZ/usr/local/bin/pawos-enviar-correo-cita"
install -m 755 pawos-enviar-whatsapp-cita        "$RAIZ/usr/local/bin/pawos-enviar-whatsapp-cita"
install -m 755 pawos-generar-pdf-cita.py         "$RAIZ/usr/local/bin/pawos-generar-pdf-cita.py"

[ -f branding/pawos-icon.png ] && install -m 644 branding/pawos-icon.png "$RAIZ/usr/share/icons/pawos-icon.png\""""


def main():
    archivos = [
        (ARCHIVO_INSTALAR, ANCLA_INSTALAR, NUEVO_INSTALAR, "bloque de copia de binarios"),
        (ARCHIVO_DEB, ANCLA_DEB, NUEVO_DEB, "bloque de copia de binarios (.deb)"),
    ]

    contenidos = {}
    for ruta, ancla, _nuevo, nombre in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except FileNotFoundError:
            print(f"ERROR: no se encontro {ruta}. Corre este script desde la raiz del repo.")
            sys.exit(1)
        if contenido.count(ancla) != 1:
            print(f"ERROR: en {ruta}, no se encontro (o se encontro mas de una vez) el '{nombre}'.")
            print("       No se cambio nada.")
            sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, ancla, nuevo, _nombre in archivos:
        contenido = contenidos[ruta].replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak3")
        print(f"Backup creado: {ruta}.bak3")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Listo. No hace falta recompilar nada (son scripts bash, no C),")
    print("pero si quieres verificar la sintaxis de los .sh:")
    print("  bash -n instalar-pawos.sh")
    print("  bash -n construir-deb.sh")


if __name__ == "__main__":
    main()
