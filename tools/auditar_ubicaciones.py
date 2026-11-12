"""Revisa que la ubicación de cada sitio de la lista cuadre con su dirección.

Sin internet: usa los datos de OpenStreetMap descargados en osm/.
  1) código postal de la dirección  → ¿hay sitios de OSM con ese código postal cerca?
  2) calle de la dirección          → ¿la calle pasa cerca del punto?
  3) nombre                         → si OSM tiene un local con el mismo nombre, ¿está en el mismo sitio?
Escribe tools/auditoria_ubicaciones.json con los sitios dudosos y una propuesta de coordenada.
"""
import json, glob, re, sys, math, pathlib, unicodedata, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from ubicar import load_data  # noqa

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()
def km(a, b, c, d):
    p = math.pi / 180; x = (d - b) * p * math.cos((a + c) / 2 * p); y = (c - a) * p
    return 6371 * math.hypot(x, y)
STOP = {'calle','c','de','del','la','las','los','el','avenida','av','avda','paseo','p','plaza','pl','pza','glorieta','camino','ronda','travesia','cuesta','costanilla','carrera','y','madrid','espana','s','n'}
def street_key(s):
    w = [x for x in norm(s).split() if x not in STOP and not x.isdigit()]
    return ' '.join(w)

def main():
    _, _, data = load_data()
    by_pc = collections.defaultdict(list); by_st = collections.defaultdict(list); by_name = collections.defaultdict(list)
    for f in glob.glob(str(ROOT / 'osm' / '*_*.json')):
        for lat, lon, t in json.loads(pathlib.Path(f).read_text(encoding='utf-8')):
            if t.get('addr:postcode'): by_pc[t['addr:postcode'].strip()].append((lat, lon))
            if t.get('addr:street'):
                hn = re.match(r'\d+', t.get('addr:housenumber') or '')
                by_st[street_key(t['addr:street'])].append((lat, lon, int(hn.group()) if hn else None))
            if t.get('name'): by_name[norm(t['name'])].append((lat, lon, t))
    out = []
    for d in data:
        if not isinstance(d.get('lat'), (int, float)) or d.get('osm'): continue
        la, lo = d['lat'], d['lon']; motivos = []; propuesta = None
        addr = d.get('addr') or ''
        pc = re.search(r'\b(28\d{3})\b', addr)
        if pc and len(by_pc.get(pc.group(1), [])) >= 8:
            dist = min(km(la, lo, a, b) for a, b in by_pc[pc.group(1)])
            if dist > 0.6: motivos.append(f'código postal {pc.group(1)} queda a {dist:.1f} km')
        st = None; num = None
        if addr:
            first = addr.split(',')[0]; m = re.search(r',\s*(\d+)', addr)
            st = street_key(first); num = int(m.group(1)) if m else None
            pts = by_st.get(st) or []
            if len(pts) >= 3:
                dist = min(km(la, lo, a, b) for a, b, _ in pts)
                if dist > 0.45:
                    motivos.append(f'la calle «{first.strip()}» queda a {dist:.1f} km')
                    # propuesta: portal de la misma calle con el número más cercano (mismo lado si se puede)
                    if num is not None:
                        cand = [p for p in pts if p[2] is not None]
                        if cand:
                            cand.sort(key=lambda p: (abs(p[2] - num) + (0 if p[2] % 2 == num % 2 else 1000)))
                            a, b, n2 = cand[0]
                            if abs(n2 - num) <= 20: propuesta = (round(a, 6), round(b, 6), f'portal {n2} de la misma calle (OSM)')
        nm = by_name.get(norm(d['n'])) or []
        if nm:
            dmin = min(km(la, lo, a, b) for a, b, _ in nm)
            if dmin > 0.35 and len(nm) <= 2:
                motivos.append(f'en OSM «{d["n"]}» está a {dmin:.1f} km')
                if not propuesta:
                    # el de OSM que mejor encaja con la dirección
                    best = None
                    for a, b, t in nm:
                        ok = 0
                        if pc and t.get('addr:postcode', '').strip() == pc.group(1): ok += 2
                        if st and street_key(t.get('addr:street', '')) == st: ok += 3
                        if best is None or ok > best[0]: best = (ok, a, b, t)
                    if best and (best[0] > 0 or not addr):
                        propuesta = (round(best[1], 6), round(best[2], 6), 'mismo local en OpenStreetMap')
        if motivos:
            out.append({'n': d['n'], 'z': d.get('z'), 'addr': addr, 'lat': la, 'lon': lo, 'locSrc': d.get('locSrc'), 'motivos': motivos, 'propuesta': propuesta})
    (ROOT / 'tools' / 'auditoria_ubicaciones.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(out)} sitios dudosos de {sum(1 for d in data if isinstance(d.get("lat"), (int, float)))} con coordenadas; {sum(1 for o in out if o["propuesta"])} con propuesta')

if __name__ == '__main__':
    main()
