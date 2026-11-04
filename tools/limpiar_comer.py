"""Verifica el catálogo «Dónde comer» (comer-offline.json) contra OpenStreetMap.

Los candidatos sin verificar se conservan solo si aparecen en el mapa abierto con ese nombre
y en su municipio; se les añade ubicación, dirección y web. El resto se elimina
(copia de seguridad en tools/comer_eliminados.json). Sin coste: no usa Google.
"""
import json, re, sys, pathlib, unicodedata
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ubicar import sim, km, tokens, http, OVERPASS, strip
import urllib.parse, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BBOX = '39.88,-4.58,41.17,-3.05'   # Comunidad de Madrid

def descargar():
    q = ('[out:csv(::lat,::lon,name,amenity,cuisine,"addr:street","addr:housenumber","addr:city",website,"contact:website";true;"\\t")]'
         f'[timeout:240][bbox:{BBOX}];(nwr["name"]["amenity"~"^(restaurant|fast_food|cafe|bar|pub|ice_cream|food_court)$"];);out center;')
    for intento in range(3):
        for ep in OVERPASS:
            try:
                return http(ep, data=urllib.parse.urlencode({'data': q}).encode(), timeout=300)
            except Exception as ex:
                print('Overpass', ep, 'falló:', ex)
        time.sleep(30)
    raise SystemExit('No se pudo descargar el mapa abierto')

def main():
    txt = open(sys.argv[1], encoding='utf-8').read() if len(sys.argv) > 1 else descargar()
    rows = txt.split('\n'); head = rows.pop(0).split('\t'); col = {k: i for i, k in enumerate(head)}
    pois = []
    for l in rows:
        c = l.split('\t')
        if len(c) < len(head) or not c[col['name']]: continue
        g = lambda k: c[col[k]]
        try: pois.append({'lat': float(g('@lat')), 'lon': float(g('@lon')), 'name': g('name'), 'city': strip(g('addr:city')),
                          'addr': (g('addr:street') + (' ' + g('addr:housenumber') if g('addr:housenumber') else '')).strip(),
                          'web': g('website') or g('contact:website')})
        except ValueError: pass
    print(len(pois), 'locales en el mapa abierto')
    idx = {}
    for k, p in enumerate(pois):
        for t in set(tokens(p['name'])):
            if len(t) >= 3: idx.setdefault(t, []).append(k)
    # Centro aproximado de cada municipio: mediana de los locales con esa ciudad en su dirección
    cent = {}
    for p in pois:
        if p['city']: cent.setdefault(p['city'], []).append((p['lat'], p['lon']))
    med = lambda v: sorted(v)[len(v) // 2]
    cent = {k: (med([a for a, _ in v]), med([b for _, b in v])) for k, v in cent.items() if len(v) >= 5}
    cent.setdefault('madrid', (40.4168, -3.7038))

    path = ROOT / 'comer-offline.json'
    data = json.load(open(path, encoding='utf-8'))
    kept, removed = [], []
    for o in data:
        if o.get('verified') and o.get('status') != 'Candidato sin verificación individual':
            kept.append(o); continue
        area = strip(o.get('area') or 'madrid')
        c = cent.get(area) or next((v for k, v in cent.items() if area in k or k in area), None)
        best = None
        for k in {k for t in tokens(o['name']) for k in idx.get(t, [])}:
            p = pois[k]; s = sim(o['name'], p['name'])
            if s < .85: continue
            if c and km(c[0], c[1], p['lat'], p['lon']) > 12: continue
            if not c and s < .95: continue
            if not best or s > best[0]: best = (s, p)
        if not best:
            removed.append(o); continue
        p = best[1]
        o.update({'verified': True, 'status': 'Verificado en el mapa', 'lat': round(p['lat'], 6), 'lon': round(p['lon'], 6),
                  'note': (p['addr'] + '. ' if p['addr'] else '') + 'Ubicación comprobada en OpenStreetMap; confirma horario antes de ir.',
                  'maps': 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(f"{o['name']} {p['lat']:.6f},{p['lon']:.6f}")})
        if p['web']: o['web'] = p['web']
        kept.append(o)
    # sin duplicados (mismo nombre y municipio)
    seen, final = set(), []
    for o in kept:
        k = (strip(o['name']), strip(o.get('area')))
        if k in seen: continue
        seen.add(k); final.append(o)
    json.dump(final, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(removed, open(ROOT / 'tools' / 'comer_eliminados.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'Dónde comer: {len(data)} → {len(final)} (verificados en el mapa: {sum(1 for o in final if o.get("status") == "Verificado en el mapa")}, eliminados: {len(removed)})')

if __name__ == '__main__':
    main()
