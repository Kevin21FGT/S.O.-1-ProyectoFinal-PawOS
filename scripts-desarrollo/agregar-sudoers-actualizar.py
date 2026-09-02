#!/usr/bin/env python3
"""
agregar-sudoers-actualizar.py

Ahora mismo, "Buscar Actualizaciones" pide la contrasena de sudo de
quien lo corre para poder copiar los binarios nuevos a
/usr/local/bin (carpeta protegida). Eso funciona si esa persona tiene
permisos de administrador en Linux, pero NO funcionaria para un
compañero cuya cuenta no tenga sudo.

Fix: agregar una regla de sudoers bien acotada -- SOLO estos 5
comandos exactos (copiar/mover/dar permisos a los binarios ya
compilados en /opt/pawos-src), nada mas -- para el grupo
pawos-refugio (al que ya pertenece cualquier colaborador gracias al
postinst). Asi cualquiera puede actualizar sin contrasena, sin
recibir sudo completo. Mismo patron que ya se uso para
pawos-apagar (poweroff/reboot) y pawos-respaldo.

Toca:
  - instalar-pawos.sh: agrega el archivo /etc/sudoers.d/pawos-actualizar
    justo despues de crear /etc/sudoers.d/pawos-respaldo.
  - construir-deb.sh: agrega el mismo archivo dentro del arbol del
    paquete ($RAIZ/etc/sudoers.d/pawos-actualizar) y lo suma al chmod 440.

Uso: parado en la raiz del repo:
    python3 agregar-sudoers-actualizar.py
"""

import shutil
import sys

ARCHIVO_INSTALAR = "instalar-pawos.sh"
ARCHIVO_DEB = "construir-deb.sh"

REGLA_ACTUALIZAR = (
    "%pawos-refugio ALL=(ALL) NOPASSWD: "
    "/usr/bin/cp /opt/pawos-src/pawos-refugio-gui /usr/local/bin/pawos-refugio-gui.new, "
    "/usr/bin/cp /opt/pawos-src/pawos-refugio /usr/local/bin/pawos-refugio.new, "
    "/usr/bin/chmod 755 /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio.new, "
    "/usr/bin/mv -f /usr/local/bin/pawos-refugio-gui.new /usr/local/bin/pawos-refugio-gui, "
    "/usr/bin/mv -f /usr/local/bin/pawos-refugio.new /usr/local/bin/pawos-refugio"
)

# ---------------------------------------------------------------
# instalar-pawos.sh
# ---------------------------------------------------------------
ANCLA_INSTALAR = """cat > /etc/sudoers.d/pawos-respaldo << 'SUDOEOF2'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
SUDOEOF2
chmod 440 /etc/sudoers.d/pawos-respaldo"""
NUEVO_INSTALAR = f"""cat > /etc/sudoers.d/pawos-respaldo << 'SUDOEOF2'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
SUDOEOF2
chmod 440 /etc/sudoers.d/pawos-respaldo
cat > /etc/sudoers.d/pawos-actualizar << 'SUDOEOF3'
{REGLA_ACTUALIZAR}
SUDOEOF3
chmod 440 /etc/sudoers.d/pawos-actualizar"""

# ---------------------------------------------------------------
# construir-deb.sh
# ---------------------------------------------------------------
ANCLA_DEB = """cat > "$RAIZ/etc/sudoers.d/pawos-respaldo" << 'EOF'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
EOF
chmod 440 "$RAIZ/etc/sudoers.d/pawos-apagar" "$RAIZ/etc/sudoers.d/pawos-respaldo\""""
NUEVO_DEB = f"""cat > "$RAIZ/etc/sudoers.d/pawos-respaldo" << 'EOF'
%pawos-admin ALL=(ALL) NOPASSWD: /usr/bin/systemctl --no-block start pawos-backup.service, /usr/local/bin/pawos-configurar-respaldo, /usr/local/bin/pawos-listar-respaldos, /usr/local/bin/pawos-restaurar-nube, /usr/local/bin/pawos-backup-nube
EOF
cat > "$RAIZ/etc/sudoers.d/pawos-actualizar" << 'EOF'
{REGLA_ACTUALIZAR}
EOF
chmod 440 "$RAIZ/etc/sudoers.d/pawos-apagar" "$RAIZ/etc/sudoers.d/pawos-respaldo" "$RAIZ/etc/sudoers.d/pawos-actualizar\""""


def main():
    archivos = [
        (ARCHIVO_INSTALAR, ANCLA_INSTALAR, NUEVO_INSTALAR, "bloque sudoers pawos-respaldo"),
        (ARCHIVO_DEB, ANCLA_DEB, NUEVO_DEB, "bloque sudoers pawos-respaldo (.deb)"),
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
        shutil.copy(ruta, ruta + ".bak")
        print(f"Backup creado: {ruta}.bak")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"{ruta} parchado OK.")

    print("")
    print("Para probar ESTA VM ahora mismo (una sola vez, sin reinstalar el .deb):")
    print("")
    print("  sudo tee /etc/sudoers.d/pawos-actualizar > /dev/null << 'EOF'")
    print(REGLA_ACTUALIZAR)
    print("EOF")
    print("  sudo chmod 440 /etc/sudoers.d/pawos-actualizar")


if __name__ == "__main__":
    main()
