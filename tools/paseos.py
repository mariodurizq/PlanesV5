"""Genera paseos.json: lugares bonitos para pasear en toda la Comunidad de Madrid.

Fuente: OpenStreetMap (Overpass), gratis. Se queda con plazas, parques, jardines, miradores, monumentos,
palacios, castillos, museos, puentes… que tengan nombre y ficha en Wikidata/Wikipedia (señal de que son
conocidos), más los parques y jardines con nombre. La web usa estos puntos para trazar paseos «de camino».
"""
import json, math, re, time, pathlib, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVIDORES = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
              'https://overpass.private.coffee/api/interpreter']
Q = """[out:json][timeout:240];
area["ISO3166-2"="ES-MD"]->.a;
(
  nwr["tourism"~"^(attraction|viewpoint|museum|gallery)$"]["name"](area.a);
  nwr["historic"~"^(monument|castle|monastery|palace|city_gate|fort|ruins|archaeological_site|aqueduct|tower|church|building|memorial|manor)$"]["name"](area.a);
  nwr["leisure"~"^(park|garden|nature_reserve)$"]["name"](area.a);
  nwr["place"="square"]["name"](area.a);
  nwr["natural"~"^(peak|waterfall)$"]["name"](area.a);
  way["highway"="pedestrian"]["name"]["wikidata"](area.a);
  nwr["amenity"="marketplace"]["name"]["wikidata"](area.a);
  nwr["man_made"~"^(bridge|lighthouse|tower)$"]["name"]["wikidata"](area.a);
);
out center tags;"""

TIPOS = [  # (condición, etiqueta, peso)
    (lambda t: t.get('tourism') == 'viewpoint', 'mirador', 3),
    (lambda t: t.get('place') == 'square', 'plaza', 3),
    (lambda t: t.get('leisure') == 'garden', 'jardín', 3),
    (lambda t: t.get('leisure') == 'park', 'parque', 3),
    (lambda t: t.get('leisure') == 'nature_reserve', 'espacio natural', 2),
    (lambda t: t.get('historic') == 'castle', 'castillo', 3),
    (lambda t: t.get('historic') == 'palace', 'palacio', 3),
    (lambda t: t.get('historic') == 'city_gate', 'puerta histórica', 3),
    (lambda t: t.get('historic') == 'monastery', 'monasterio', 3),
    (lambda t: t.get('historic') in ('ruins', 'archaeological_site', 'fort'), 'restos históricos', 2),
    (lambda t: t.get('historic') == 'aqueduct', 'acueducto', 2),
    (lambda t: t.get('historic') == 'monument', 'monumento', 2),
    (lambda t: t.get('historic') == 'memorial', 'monumento', 1),
    (lambda t: t.get('historic') == 'church' or t.get('amenity') == 'place_of_worship', 'iglesia', 1),
    (lambda t: t.get('tourism') in ('museum', 'gallery'), 'museo', 2),
    (lambda t: t.get('highway') == 'pedestrian', 'calle peatonal', 3),
    (lambda t: t.get('amenity') == 'marketplace', 'mercado', 2),
    (lambda t: t.get('man_made') == 'bridge' or t.get('bridge'), 'puente', 2),
    (lambda t: t.get('natural') == 'waterfall', 'cascada', 2),
    (lambda t: t.get('natural') == 'peak', 'cima', 1),
    (lambda t: t.get('historic') in ('tower', 'building', 'manor') or t.get('man_made') == 'tower', 'edificio histórico', 1),
    (lambda t: t.get('tourism') == 'attraction', 'lugar de interés', 2),
]
EVITAR = re.compile(r'\b(parque infantil|zona infantil|área canina|area canina|pipican|parking|aparcamiento|cementerio|tanatorio|'
                    r'colegio|instituto|polideportivo|campo de fútbol|depuradora|rotonda|glorieta de tráfico)\b', re.I)


def overpass():
    for url in SERVIDORES:
        for _ in range(2):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': Q}).encode(),
                                             headers={'User-Agent': 'radar-planes-madrid/1.0'})
                with urllib.request.urlopen(req, timeout=300) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print('Overpass falló', url, e); time.sleep(15)
    raise SystemExit('Ningún servidor de Overpass respondió')


def km(a, b):
    return math.hypot((a['lat'] - b['lat']) * 111, (a['lon'] - b['lon']) * 85)


def main():
    data = overpass()
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {})
        n = t.get('name:es') or t.get('name')
        c = el.get('center') or ({'lat': el['lat'], 'lon': el['lon']} if 'lat' in el else None)
        if not n or not c or EVITAR.search(n): continue
        tipo, peso = None, 0
        for cond, et, pw in TIPOS:
            if cond(t): tipo, peso = et, pw; break
        if not tipo: continue
        conocido = bool(t.get('wikidata') or t.get('wikipedia'))
        nombre_parque = tipo in ('parque', 'jardín') and re.match(r'(parque|jard[ií]n|jardines|quinta|dehesa|finca|real jard)', n, re.I)
        if not conocido and not nombre_parque: continue
        if tipo == 'iglesia' and not t.get('wikipedia'): continue
        if not conocido and tipo in ('parque', 'jardín'): peso = 1   # parques de barrio: válidos, pero con menos prioridad
        out.append({'n': n, 'lat': round(c['lat'], 5), 'lon': round(c['lon'], 5), 'k': tipo,
                    'w': peso + (2 if t.get('wikipedia') else 1 if conocido else 0)})
    # quitar repetidos (mismo nombre a menos de 300 m) quedándose con el de más peso
    out.sort(key=lambda x: -x['w'])
    final = []
    for p in out:
        if any(q['n'].lower() == p['n'].lower() and km(p, q) < 0.3 for q in final): continue
        final.append(p)
    final.sort(key=lambda x: (x['lat'], x['lon']))
    if len(final) < 300: raise SystemExit(f'Solo {len(final)} lugares: algo ha ido mal, no se sobrescribe')
    (ROOT / 'paseos.json').write_text(json.dumps({'generado': time.strftime('%Y-%m-%d'), 'lugares': final},
                                                 ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    from collections import Counter
    print(len(final), 'lugares', Counter(p['k'] for p in final).most_common())


if __name__ == '__main__':
    main()
