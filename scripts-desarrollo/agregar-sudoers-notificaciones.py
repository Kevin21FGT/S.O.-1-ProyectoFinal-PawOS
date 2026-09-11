#!/usr/bin/env python3
"""
agregar-sudoers-notificaciones.py

Agrega la regla de sudoers para las notificaciones de citas:
  - pawos-configurar-notificaciones: solo pawos-admin (cambiar las
    credenciales es sensible, solo el Administrador deberia poder).
  - pawos-enviar-correo-cita / pawos-enviar-whatsapp-cita: todo el
    grupo pawos-refugio (cualquier colaborador deberia poder disparar
    un recordatorio al registrar una cita, sin necesitar ver las
    credenciales -- los scripts las leen ellos mismos, corriendo
    como root via esta regla).

Sigue exactamente el mismo patron ya usado para pawos-apagar,
pawos-respaldo y pawos-actualizar.

Requisito: correr DESPUES de agregar-sudoers-actualizar.py (usa el
bloque de pawos-actualizar como ancla).

Uso: parado en la raiz del repo:
    python3 agregar-sudoers-notificaciones.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"

REGLA_ADMIN = "%pawos-admin ALL=(ALL) NOPASSWD: /usr/local/bin/pawos-configurar-notificaciones"
REGLA_REFUGIO = "%pawos-refugio ALL=(ALL) NOPASSWD: /usr/local/bin/pawos-enviar-correo-cita, /usr/local/bin/pawos-enviar-whatsapp-cita"

# ---------------------------------------------------------------
# instalar-pawos.sh
# ---------------------------------------------------------------
ANCLA_INSTALAR = """cat > /etc/sudoers.d/pawos-actualizar << 'SUDOEOF3'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
SUDOEOF3
chmod 440 /etc/sudoers.d/pawos-actualizar"""
NUEVO_INSTALAR = f"""cat > /etc/sudoers.d/pawos-actualizar << 'SUDOEOF3'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
SUDOEOF3
chmod 440 /etc/sudoers.d/pawos-actualizar
cat > /etc/sudoers.d/pawos-notificaciones << 'SUDOEOF4'
{REGLA_ADMIN}
{REGLA_REFUGIO}
SUDOEOF4
chmod 440 /etc/sudoers.d/pawos-notificaciones"""

# ---------------------------------------------------------------
# construir-deb.sh
# ---------------------------------------------------------------
ANCLA_DEB = """cat > "$RAIZ/etc/sudoers.d/pawos-actualizar" << 'EOF'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
EOF
chmod 440 "$RAIZ/etc/sudoers.d/pawos-apagar" "$RAIZ/etc/sudoers.d/pawos-respaldo" "$RAIZ/etc/sudoers.d/pawos-actualizar\""""
NUEVO_DEB = f"""cat > "$RAIZ/etc/sudoers.d/pawos-actualizar" << 'EOF'
%pawos-refugio ALL=(ALL) NOPASSWD: /usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, /usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, /usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, /usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, /usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio
EOF
cat > "$RAIZ/etc/sudoers.d/pawos-notificaciones" << 'EOF'
{REGLA_ADMIN}
{REGLA_REFUGIO}
EOF
chmod 440 "$RAIZ/etc/sudoers.d/pawos-apagar" "$RAIZ/etc/sudoers.d/pawos-respaldo" "$RAIZ/etc/sudoers.d/pawos-actualizar" "$RAIZ/etc/sudoers.d/pawos-notificaciones\""""


def main():
    archivos = [
        (ARCHIVO_INSTALAR, ANCLA_INSTALAR, NUEVO_INSTALAR, "bloque sudoers pawos-actualizar"),
        (ARCHIVO_DEB, ANCLA_DEB, NUEVO_DEB, "bloque sudoers pawos-actualizar (.deb)"),
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
            print("       Puede que agregar-sudoers-actualizar.py no se haya aplicado todavia,")
            print("       o que el archivo ya haya sido modificado. No se cambio nada.")
            sys.exit(1)
        contenidos[ruta] = contenido

    for ruta, ancla, nuevo, _nombre in archivos:
        contenido = contenidos[ruta].replace(ancla, nuevo, 1)
        shutil.copy(ruta, ruta + ".bak2")
        print(f"Backup creado: {ruta}.bak2")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Para probar ESTA VM ahora mismo (una sola vez, sin reinstalar el .deb):")
    print("")
    print("  sudo tee /etc/sudoers.d/pawos-notificaciones > /dev/null << 'EOF'")
    print(REGLA_ADMIN)
    print(REGLA_REFUGIO)
    print("EOF")
    print("  sudo chmod 440 /etc/sudoers.d/pawos-notificaciones")


if __name__ == "__main__":
    main()
