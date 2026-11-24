#!/usr/bin/env bash
# Prepara en la carpeta indicada (por defecto _site) todos los archivos de la web, igual que se publican.
# Lo usan la publicación en GitHub Pages y la app de iPhone (app/www).
set -e
DEST="${1:-_site}"
mkdir -p "$DEST"
cp -r index.html verificar.html plan.html legal.html plan-share.js fonts osm widget vendor brand favicon.ico manifest.webmanifest service-worker.js .nojekyll *.png *.jpg *.json "$DEST"/ 2>/dev/null || true
[ -d icons ] && cp -r icons "$DEST"/ || true
python3 tools/paginas.py "$DEST" || echo "AVISO: no se pudieron generar las páginas por zona"
python3 tools/widget.py "$DEST" || echo "AVISO: no se pudo generar widget.json"
python3 tools/discotecas.py "$DEST" || echo "AVISO: no se pudo generar discotecas.json"
python3 tools/museos.py "$DEST" || echo "AVISO: no se pudo generar museos.json"
ls "$DEST" | head -50
