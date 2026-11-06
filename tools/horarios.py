"""Cada semana: horarios de apertura desde OpenStreetMap para tus sitios y los de nuevos.json.

Empareja por nombre y por cercanía real (≤150 m, o ≤400 m si el nombre coincide casi exacto).
Guarda el horario en formato OSM (campo «oh»), que la app usa para «Abierto ahora». Sin Google, sin coste.
"""
import json, sys, datetime, pathlib, urllib.parse, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ubicar import sim, km, tokens, http, OVERPASS, load_data

ROOT = pathlib.Path(__file__).resolve().parent.parent

def descargar(pts):
    s = min(p[0] for p in pts) - .02; n = max(p[0] for p in pts) + .02
    w = min(p[1] for p in pts) - .02; e = max(p[1] for p in pts) + .02
    q = ('[out:csv(::lat,::lon,name,opening_hours;true;"\\t")]'
         f'[timeout:180][bbox:{s:.3f},{w:.3f},{n:.3f},{e:.3f}];(nwr["name"]["opening_hours"];);out center;')
    for intento in range(3):
        for ep in OVERPASS:
            try: return http(ep, data=urllib.parse.urlencode({'data': q}).encode(), timeout=240)
            except Exception as ex: print('Overpass', ep, 'falló:', ex)
        time.sleep(30)
    raise SystemExit('No se pudo descargar el mapa abierto')

def main():
    lines, i, data = load_data()
    npath = ROOT / 'nuevos.json'
    nuevos = json.loads(npath.read_text(encoding='utf-8')) if npath.exists() else {'sitios': []}
    todos = [d for d in data + nuevos.get('sitios', []) if d.get('locationVerified') and isinstance(d.get('lat'), (int, float))]
    txt = open(sys.argv[1], encoding='utf-8').read() if len(sys.argv) > 1 else descargar([(d['lat'], d['lon']) for d in todos])
    rows = txt.split('\n'); rows.pop(0)
    pois = []
    for l in rows:
        c = l.split('\t')
        if len(c) < 4 or not c[2] or not c[3]: continue
        try: pois.append({'lat': float(c[0]), 'lon': float(c[1]), 'name': c[2], 'oh': c[3]})
        except ValueError: pass
    idx = {}
    for k, p in enumerate(pois):
        for t in set(tokens(p['name'])):
            if len(t) >= 3: idx.setdefault(t, []).append(k)
    nuevos_h = cambiados = 0
    for d in todos:
        best = None
        for k in {k for t in tokens(d['n']) for k in idx.get(t, [])}:
            p = pois[k]; s = sim(d['n'], p['name']); dist = km(d['lat'], d['lon'], p['lat'], p['lon'])
            if s < .8 or dist > (.4 if s >= .95 else .15): continue
            if not best or (s - dist) > best[0]: best = (s - dist, p)
        if not best: continue
        oh = best[1]['oh'].strip()
        if oh.lower() in ('closed', 'off'): continue
        if not d.get('oh'): nuevos_h += 1
        elif d['oh'] != oh: cambiados += 1
        else: continue
        d['oh'] = oh; d['ohFecha'] = datetime.date.today().isoformat()
        d.pop('hours', None)
    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')
    if npath.exists(): npath.write_text(json.dumps(nuevos, ensure_ascii=False), encoding='utf-8')
    total = sum(1 for d in todos if d.get('oh'))
    print(f'{len(pois)} locales con horario en el mapa · {nuevos_h} horarios nuevos · {cambiados} actualizados · {total} sitios con horario')

if __name__ == '__main__':
    main()
