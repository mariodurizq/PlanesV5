"""Aplica verificacion.json (generado por verificar.html) al catálogo de la app.

Uso:  python3 tools/aplicar_verificacion.py verificacion.json
- Tu lista (DATA en index.html): pone coordenadas y horarios reales, elimina los cerrados
  y los que no existen, y marca los dudosos como "Sin confirmar".
- «Dónde comer» (comer-offline.json): elimina los cerrados y los candidatos que no aparecen
  en ningún mapa; marca como verificados los encontrados.
Escribe un resumen en tools/ultima_verificacion.txt.
"""
import json, sys, re, datetime, urllib.parse, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
ver = json.load(open(sys.argv[1], encoding='utf-8'))
fecha = ver.get('generado', '')[:10] or datetime.date.today().isoformat()
sitios = ver['sitios']
cat = {s['name']: s for s in sitios if s['list'] == 'catalogo'}
com = {(s['name'], s.get('zone') or ''): s for s in sitios if s['list'] == 'comer'}

# --- Tu lista ---
html_path = root / 'index.html'
html = html_path.read_text(encoding='utf-8')
lines = html.split('\n')
idx = next(i for i, l in enumerate(lines) if l.strip().startswith('const DATA = ['))
data = json.loads(re.sub(r'^\s*const DATA = ', '', lines[idx]).rstrip().rstrip(';'))
kept, removed, stats = [], [], {'ok': 0, 'sin_confirmar': 0, 'cerrado_temp': 0}
for d in data:
    v = cat.get(d['n'])
    if not v:
        kept.append(d); continue
    st = v['status']
    if st in ('cerrado', 'no_existe'):
        removed.append(f"{d['n']} ({d.get('z') or 'sin zona'}): {v.get('detail') or st}")
        continue
    if st == 'ok' and 'lat' in v:
        d['lat'], d['lon'] = v['lat'], v['lon']
        d['locationVerified'] = True
        d['verifiedAt'] = fecha
        if v.get('periods'): d['hours'] = v['periods']
        if v.get('web'): d['web'] = v['web']
        if v.get('addr'): d['addr'] = v['addr']
        if d.get('e') in ('Sin confirmar', 'Revisar (posible cierre)', ''): d['e'] = 'Abierto'
        if not d.get('v') and v.get('rating'): d['v'], d['nr'] = v['rating'], v.get('nr') or 0
    elif st == 'cerrado_temp':
        d['e'] = 'Cerrado temporalmente'
    else:
        # Sin coordenadas reales: se quitan los centros de barrio para que no confundan
        d['e'] = 'Sin confirmar'
        d.pop('locationVerified', None)
    stats[st] = stats.get(st, 0) + 1
    kept.append(d)
lines[idx] = 'const DATA = ' + json.dumps(kept, ensure_ascii=False) + ';'
html_path.write_text('\n'.join(lines), encoding='utf-8')

# --- «Dónde comer» ---
off_path = root / 'comer-offline.json'
off = json.load(open(off_path, encoding='utf-8'))
off_kept, off_removed, off_ok = [], 0, 0
for o in off:
    v = com.get((o['name'], o.get('area') or ''))
    if v:
        if v['status'] in ('cerrado', 'no_existe') or (v['status'] == 'sin_confirmar' and not o.get('verified')):
            off_removed += 1; continue
        if v['status'] == 'ok':
            off_ok += 1
            o['verified'] = True
            o['status'] = 'Ubicación verificada en el mapa'
            o['note'] = (v.get('addr') + '. ' if v.get('addr') else '') + 'Comprueba horario antes de ir.'
            o['lat'], o['lon'] = v.get('lat'), v.get('lon')
            o['maps'] = 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(f"{o['name']} {v.get('lat')},{v.get('lon')}")
    off_kept.append(o)
json.dump(off_kept, open(off_path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

resumen = [f'Verificación del {fecha} ({ver.get("fuente","")})',
           f'Tu lista: {len(data)} → {len(kept)} sitios. Verificados {stats.get("ok",0)}, sin confirmar {stats.get("sin_confirmar",0)}, cerrados temporalmente {stats.get("cerrado_temp",0)}, eliminados {len(removed)}.',
           f'Dónde comer: {len(off)} → {len(off_kept)} entradas. Verificadas {off_ok}, eliminadas {off_removed}.',
           '', 'Eliminados de tu lista:'] + ['- ' + r for r in removed]
(root / 'tools' / 'ultima_verificacion.txt').write_text('\n'.join(resumen) + '\n', encoding='utf-8')
print('\n'.join(resumen[:3]))
