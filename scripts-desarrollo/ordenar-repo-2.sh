#!/bin/bash
# ordenar-repo-2.sh (v2: seguro para volver a correr)
#
# Segunda pasada de ordenar-repo.sh: mueve a scripts-desarrollo/ los
# scripts de parches puntuales (ya aplicados) que se fueron
# acumulando en la raiz del repo desde la ultima vez que se ordeno.
#
# Usa "git mv" para los archivos que ya estan en git (asi conserva su
# historial), y "mv" normal para los que todavia no se han comiteado
# (git mv no funciona con archivos sin rastrear). Es seguro volver a
# correrlo: si un archivo ya no esta en la raiz (porque ya se movio en
# una corrida anterior), simplemente se omite.
#
# NO toca (siguen en uso o ya organizados): instalar-pawos.sh,
# construir-deb.sh, instalar-en-vm.sh, limpiar-backups.sh,
# propagar-combinada.sh, Makefile, README.md,
# PawOS_Manual_Usuario.docx, .gitignore, scripts/, src/, include/,
# live-build-config/, y los scripts que corren en produccion:
# pawos-actualizar-gui, pawos-notificar-cita,
# pawos-configurar-notificaciones, pawos-enviar-correo-cita,
# pawos-enviar-whatsapp-cita, pawos-generar-pdf-cita.py.
#
# Uso: parado en la raiz del repo:
#   bash ordenar-repo-2.sh
set -e
echo "==> Moviendo scripts de desarrollo a scripts-desarrollo/..."
SCRIPTS_DEV=(
    agregar-administrar-colaboradores.py
    agregar-asistente-bienvenida.py
    agregar-boton-regresar.py
    agregar-clientes-colaboradores.py
    agregar-login-gui.py
    agregar-pantalla-notificaciones.py
    agregar-roles-cliente.py
    agregar-roles-rescatista-recepcionista.py
    agregar-selector-cliente-vacunas.py
    agregar-sudoers-actualizar.py
    agregar-sudoers-notificaciones.py
    agregar-telefono-cliente.py
    arreglar-cierre-asistente.py
    arreglar-cierre-colaboradores.py
    arreglar-opt-pawos-src.py
    arreglar-posesion-dudosa-git.py
    arreglar-umask-actualizar.py
    arreglar-usuario-corrupto-admin.py
    clasificar-modulos.py
    conectar-envio-recordatorio.py
    diferenciar-correo-no-registrado.py
    documentar-instalador-deb.py
    instalar-scripts-notificaciones.py
    ocultar-acceso-admin.py
    quitar-rol-registro-agregar-admin-clientes.py
    separar-binario-producto.py
    subir-version-1.3.py
    subir-version-1.4.py
    subir-version-1.5.py
    subir-version-1.6.py
    subir-version-1.7.py
    subir-version-1.8.py
    subir-version-1.9.py
)
for f in "${SCRIPTS_DEV[@]}"; do
    if [ ! -f "$f" ]; then
        echo "  (ya no esta en la raiz, se omite: $f)"
        continue
    fi
    if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
        git mv "$f" "scripts-desarrollo/$f"
        echo "  movido (git mv, conserva historial): $f"
    else
        mv "$f" "scripts-desarrollo/$f"
        echo "  movido (mv, no estaba comiteado todavia): $f"
    fi
done
echo ""
echo "==> Moviendo este mismo script a scripts-desarrollo/..."
mv "$0" scripts-desarrollo/ordenar-repo-2.sh 2>/dev/null || true
echo ""
echo "=========================================================="
echo " Listo. Revisa con: git status"
echo " Si todo se ve bien, comitea con:"
echo ""
echo "   git add -A"
echo '   git commit -m "Ordena la raiz del repo: mueve scripts de desarrollo acumulados a scripts-desarrollo/"'
echo "   git push"
echo "=========================================================="
