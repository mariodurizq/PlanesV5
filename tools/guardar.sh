#!/usr/bin/env bash
# Ejecuta un script que modifica archivos y sube el resultado sin pisar otros cambios.
# Si mientras tanto otro proceso subió algo, se repite sobre la versión nueva (hasta 4 intentos).
# Con REPETIR=0 (procesos que usan Google) el script NO se repite —para no gastar consultas—:
# se conservan sus archivos de salida y se suben encima de la versión nueva.
# Uso: tools/guardar.sh "mensaje del commit" "comando" archivo1 archivo2 ...
set -u
MSG="$1"; CMD="$2"; shift 2
REPETIR="${REPETIR:-1}"
git config user.name "renta-bot"; git config user.email "renta-bot@users.noreply.github.com"
TMP=$(mktemp -d)
for intento in 1 2 3 4; do
  git fetch -q origin main && git reset -q --hard origin/main
  if [ "$intento" = 1 ] || [ "$REPETIR" = 1 ]; then
    bash -c "$CMD" || exit 1
    for f in "$@"; do if [ -e "$f" ]; then mkdir -p "$TMP/$(dirname "$f")"; cp "$f" "$TMP/$f"; fi; done
  else
    for f in "$@"; do if [ -e "$TMP/$f" ]; then cp "$TMP/$f" "$f"; fi; done
  fi
  for f in "$@"; do if [ -e "$f" ]; then git add "$f"; fi; done
  if git diff --cached --quiet; then echo "Sin cambios"; exit 0; fi
  git commit -q -m "$MSG"
  if git push -q origin HEAD:main; then echo "Guardado (intento $intento)"; exit 0; fi
  echo "Otro proceso subió cambios a la vez; reintento…"; sleep $((intento * 7))
done
echo "No se pudo guardar tras 4 intentos"; exit 1
