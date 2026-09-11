#!/bin/bash
# ordenar-repo.sh
#
# Ordena la raiz del repositorio: mueve los scripts sueltos de parches
# puntuales (usados durante el desarrollo, ya aplicados) a una carpeta
# scripts-desarrollo/, mueve test_memoria.c a tests/, y quita del
# control de versiones un binario viejo que ya no genera el Makefile
# actual (servidor_monitoreo) y un archivo vacio (refugio_swap.bin).
#
# Usa "git mv" para que el historial de cada archivo se conserve
# (en GitHub vas a poder seguir viendo "Sube version a 1.2..." etc.
# aunque el archivo ahora este en otra carpeta).
#
# NO toca: instalar-pawos.sh, scripts/, pawos-actualizar-gui, src/,
# include/, live-build-config/ -- esos ya estan en uso o ya organizados.
#
# Uso: parado en la raiz del repo (rama-Kevin, sin cambios pendientes):
#   bash ordenar-repo.sh

set -e

echo "==> Creando carpetas..."
mkdir -p scripts-desarrollo
mkdir -p tests

echo "==> Moviendo scripts de desarrollo a scripts-desarrollo/..."
SCRIPTS_DEV=(
    agregar-boton-actualizar.py
    agregar-guardar-reporte.py
    agregar-novedades-dialogo.py
    agregar-novedades-primera-vez.py
    agregar-reportes-categoria.py
    agregar-version.py
    aplicar-boton-actualizar.sh
    arreglar-actualizador-completo.sh
    arreglar-safe-directory.sh
    arreglar-text-file-busy.sh
    check-git-sync.sh
    check-observaciones.sh
    commit-gnome.sh
    documentar-dialogo-novedades-readme.py
    excluir-merges-novedades.py
    integrar-boton-y-commit.sh
    mejorar-diseno-pdf-y-version.py
    patch_cancelar_esc.py
    patch_cancelar_esc_v2.py
    patch_ordenar_procesos.py
    patch_vacunas.py
    redeploy-script-y-rebuild.sh
    subir-version-1.2.py
)
for f in "${SCRIPTS_DEV[@]}"; do
    if [ -f "$f" ]; then
        git mv "$f" "scripts-desarrollo/$f"
        echo "  movido: $f"
    fi
done
# agregar-login-gui.py se mueve tambien si ya lo copiaste, lo corriste
# y ya quedo comiteado (si todavia no existe o no esta en git, no pasa
# nada -- este bloque simplemente no hace nada en ese caso).
if [ -f "agregar-login-gui.py" ] && git ls-files --error-unmatch agregar-login-gui.py >/dev/null 2>&1; then
    git mv agregar-login-gui.py scripts-desarrollo/agregar-login-gui.py
    echo "  movido: agregar-login-gui.py"
fi

echo ""
echo "==> Moviendo test_memoria.c a tests/..."
if [ -f "test_memoria.c" ]; then
    git mv test_memoria.c tests/test_memoria.c
    echo "  movido: test_memoria.c"
fi

echo ""
echo "==> Quitando de git archivos que ya no deberian estar versionados..."
if git ls-files --error-unmatch servidor_monitoreo >/dev/null 2>&1; then
    git rm --cached servidor_monitoreo
    echo "  servidor_monitoreo (binario viejo, el Makefile actual genera pawos-monitoreo, no este) -- quitado de git, se borra tambien del disco"
    rm -f servidor_monitoreo
fi
if git ls-files --error-unmatch refugio_swap.bin >/dev/null 2>&1; then
    git rm --cached refugio_swap.bin
    echo "  refugio_swap.bin (archivo vacio, ya esta en .gitignore para el futuro) -- quitado de git"
fi

echo ""
echo "==> Moviendo este mismo script a scripts-desarrollo/..."
mv "$0" scripts-desarrollo/ordenar-repo.sh 2>/dev/null || true

echo ""
echo "=========================================================="
echo " Listo. Revisa con: git status"
echo " Si todo se ve bien, comitea con:"
echo ""
echo "   git add -A"
echo '   git commit -m "Ordena la raiz del repo: mueve scripts de desarrollo a scripts-desarrollo/, test a tests/, quita binario viejo"'
echo "   git push origin rama-Kevin"
echo "=========================================================="
