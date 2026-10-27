#!/bin/bash
# ordenar-repo.sh
#
# Deja ordenada la raiz del repo. NO borra nada y NO hace commit: solo mueve
# archivos (con git mv cuando ya estan en Git) para que despues revises con
# "git status" y hagas tu propio commit.
#
#   - parche-*.py y subir-version-*.py  ->  scripts-desarrollo/
#   - mensaje-commit-v*.txt             ->  scripts-desarrollo/mensajes-commit/
#   - repomix-output.xml (548 KB, es un volcado del codigo)  ->  sale de Git
#     (el archivo queda en tu carpeta, solo deja de subirse) y se ignora
#   - binario pawos-foto y copias .bak_*  ->  se ignoran en .gitignore
#
# NO se tocan: Makefile, README, el manual, instalar-*.sh, construir-deb.sh,
# propagar-combinada.sh, limpiar-backups.sh ni los scripts pawos-* (el
# instalador y el .deb los buscan en la raiz).
#
# Uso (parado en la raiz del repo):
#   bash ordenar-repo.sh

set -e

if [ ! -f Makefile ] || [ ! -d src ] || [ ! -d scripts-desarrollo ]; then
  echo "ERROR: corre esto desde la raiz del repo (donde esta el Makefile)."
  exit 1
fi

mover() {
  # mover <archivo> <carpeta_destino>
  local f="$1" dest="$2"
  [ -e "$f" ] || return 0
  mkdir -p "$dest"
  if [ -e "$dest/$(basename "$f")" ]; then
    echo "  (ya existe en $dest, se deja: $f)"
    return 0
  fi
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    git mv "$f" "$dest/"
  else
    mv "$f" "$dest/"
  fi
  echo "  $f -> $dest/"
}

echo "== Parches y scripts de version =="
for f in parche-*.py subir-version-*.py; do mover "$f" scripts-desarrollo; done

echo "== Mensajes de commit viejos =="
for f in mensaje-commit-v*.txt; do mover "$f" scripts-desarrollo/mensajes-commit; done

echo "== repomix-output.xml =="
if git ls-files --error-unmatch repomix-output.xml >/dev/null 2>&1; then
  git rm --cached -q repomix-output.xml
  echo "  sale de Git (el archivo sigue en tu carpeta)"
fi

echo "== .gitignore =="
agregar_ignore() {
  grep -qxF "$1" .gitignore 2>/dev/null || { echo "$1" >> .gitignore; echo "  + $1"; }
}
agregar_ignore "repomix-output.xml"
agregar_ignore "/pawos-foto"
agregar_ignore "*.bak_*"

echo ""
echo "Listo. Revisa con:  git status --short"
echo "Si todo se ve bien:"
echo "  git add -A"
echo "  git commit -m \"ordenar repo: parches y scripts viejos a scripts-desarrollo\""
