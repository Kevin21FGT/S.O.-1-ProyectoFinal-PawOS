#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parche-deb-3-apps-nuevas.py

Agrega las 3 apps nuevas (PawOS Vacunas GUI, PawOS Monitor, PawOS
Portal de Clientes) al instalador .deb (construir-deb.sh):
  1. Las compila junto con lo demas.
  2. Copia sus binarios dentro del paquete.
  3. Les crea su propio icono de aplicacion (.desktop).
  4. Hace que esos iconos tambien se copien al Escritorio al instalar,
     igual que ya pasa con PawOS Refugio (GUI).

Uso: parado en la raiz del repo (~/S.O.-1-ProyectoFinal-PawOS):
    python3 parche-deb-3-apps-nuevas.py
"""
import shutil
import sys
from pathlib import Path

SCRIPT = Path("construir-deb.sh")

ANCLA_COMPILAR = '''echo "=== 1. Compilando (version detectada: $VERSION) ==="
make clean
make all
make clean-gui
make gui'''

NUEVO_COMPILAR = '''echo "=== 1. Compilando (version detectada: $VERSION) ==="
make clean
make all
make clean-gui
make gui
make vacunas-gui
make monitor-gui
make portal-clientes'''

ANCLA_INSTALL = '''install -m 755 pawos-refugio        "$RAIZ/usr/local/bin/pawos-refugio"
install -m 755 pawos-vacunas-check  "$RAIZ/usr/local/bin/pawos-vacunas-check"
install -m 755 pawos-monitoreo      "$RAIZ/usr/local/bin/pawos-monitoreo"
install -m 755 pawos-refugio-gui    "$RAIZ/usr/local/bin/pawos-refugio-gui"'''

NUEVO_INSTALL = '''install -m 755 pawos-refugio        "$RAIZ/usr/local/bin/pawos-refugio"
install -m 755 pawos-vacunas-check  "$RAIZ/usr/local/bin/pawos-vacunas-check"
install -m 755 pawos-monitoreo      "$RAIZ/usr/local/bin/pawos-monitoreo"
install -m 755 pawos-refugio-gui    "$RAIZ/usr/local/bin/pawos-refugio-gui"
install -m 755 pawos-vacunas-gui     "$RAIZ/usr/local/bin/pawos-vacunas-gui"
install -m 755 pawos-monitor-gui     "$RAIZ/usr/local/bin/pawos-monitor-gui"
install -m 755 pawos-portal-clientes "$RAIZ/usr/local/bin/pawos-portal-clientes"'''

ANCLA_DESKTOP = '''cat > "$RAIZ/usr/share/applications/pawos-refugio-gui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio (GUI)
Comment=Sistema de gestion para refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-apagar.desktop" << 'EOF\''''

NUEVO_DESKTOP = '''cat > "$RAIZ/usr/share/applications/pawos-refugio-gui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Refugio (GUI)
Comment=Sistema de gestion para refugio de animales
Exec=/usr/local/bin/pawos-refugio-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-vacunas-gui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Vacunas
Comment=Agenda de vacunas del refugio
Exec=/usr/local/bin/pawos-vacunas-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-monitor-gui.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Monitor
Comment=Monitoreo de CPU, memoria, swap y disco en tiempo real
Exec=/usr/local/bin/pawos-monitor-gui
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-portal-clientes.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=PawOS Portal de Clientes
Comment=Portal para que los clientes vean sus datos y recordatorios de vacunas
Exec=/usr/local/bin/pawos-portal-clientes
Terminal=false
Icon=/usr/share/icons/pawos-icon.png
Categories=Utility;
EOF
cat > "$RAIZ/usr/share/applications/pawos-apagar.desktop" << 'EOF\''''

ANCLA_POSTINST = '''            cp /usr/share/applications/pawos-refugio.desktop     "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-refugio-gui.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-apagar.desktop      "$CARPETA/" 2>/dev/null || true
            chmod +x "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            chown "$USUARIO_REAL":"$USUARIO_REAL" "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio-gui.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-apagar.desktop" metadata::trusted true 2>/dev/null || true'''

NUEVO_POSTINST = '''            cp /usr/share/applications/pawos-refugio.desktop     "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-refugio-gui.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-vacunas-gui.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-monitor-gui.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-portal-clientes.desktop "$CARPETA/" 2>/dev/null || true
            cp /usr/share/applications/pawos-apagar.desktop      "$CARPETA/" 2>/dev/null || true
            chmod +x "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            chown "$USUARIO_REAL":"$USUARIO_REAL" "$CARPETA"/pawos-*.desktop 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-refugio-gui.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-vacunas-gui.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-monitor-gui.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-portal-clientes.desktop" metadata::trusted true 2>/dev/null || true
            gio set "$CARPETA/pawos-apagar.desktop" metadata::trusted true 2>/dev/null || true'''

REEMPLAZOS = [
    ("paso 1 (compilar)", ANCLA_COMPILAR, NUEVO_COMPILAR),
    ("paso 2 (install binarios)", ANCLA_INSTALL, NUEVO_INSTALL),
    ("paso 4 (.desktop)", ANCLA_DESKTOP, NUEVO_DESKTOP),
    ("postinst (copiar al Escritorio)", ANCLA_POSTINST, NUEVO_POSTINST),
]


def main():
    if not SCRIPT.exists():
        print("ERROR: no se encontro construir-deb.sh. Corre esto desde la raiz del repo.")
        sys.exit(1)

    contenido = SCRIPT.read_text(encoding="utf-8")

    for nombre, ancla, _ in REEMPLAZOS:
        apariciones = contenido.count(ancla)
        if apariciones == 0:
            print(f"ERROR: no se encontro el ancla de '{nombre}' en construir-deb.sh (puede que ya este parchado, o el archivo cambio).")
            sys.exit(1)
        if apariciones > 1:
            print(f"ERROR: el ancla de '{nombre}' aparece mas de una vez, no es seguro parchar.")
            sys.exit(1)

    backup = SCRIPT.with_suffix(".sh.bak_3_apps")
    shutil.copy(SCRIPT, backup)

    for nombre, ancla, nuevo in REEMPLAZOS:
        contenido = contenido.replace(ancla, nuevo, 1)
    SCRIPT.write_text(contenido, encoding="utf-8")

    print(f"  construir-deb.sh: 3 apps nuevas integradas (compilacion, binarios, iconos). Respaldo en {backup}")
    print()
    print("SIGUIENTE PASO:")
    print("  bash construir-deb.sh")


if __name__ == "__main__":
    main()
