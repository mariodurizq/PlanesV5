"""Descarga de OpenStreetMap todos los bares, restaurantes, cafeterías, discotecas, shishas, museos, ocio…
de la Comunidad de Madrid y los guarda en trocitos (osm/<fila>_<columna>.json).

Así la web busca sitios reales al instante y sin depender de que el servidor de OpenStreetMap
responda a tiempo desde el móvil. Gratis, sin claves. Se refresca una vez al mes.
"""
import json, math, time, pathlib, urllib.request, urllib.parse, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'osm'
SERVIDORES = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
              'https://overpass.private.coffee/api/interpreter']
TILE_LAT, TILE_LON = 0.04, 0.05      # ≈ 4,4 × 4,2 km
KEEP = ['name', 'amenity', 'cuisine', 'leisure', 'tourism', 'shop', 'diet:vegan', 'diet:vegetarian', 'diet:gluten_free',
        'outdoor_seating', 'roof', 'sport', 'live_music', 'opening_hours', 'addr:street', 'addr:housenumber', 'addr:city',
        'addr:postcode', 'website', 'contact:website', 'brand', 'wikidata']
Q = """[out:json][timeout:600][maxsize:1073741824];
area["ISO3166-2"="ES-MD"]->.a;
(
  nwr["name"]["amenity"~"^(restaurant|bar|pub|cafe|fast_food|nightclub|ice_cream|biergarten|hookah_lounge|food_court|karaoke_box|music_venue|theatre|arts_centre|cinema|events_venue|marketplace)$"](area.a);
  nwr["name"]["leisure"~"^(escape_game|bowling_alley|amusement_arcade|miniature_golf|trampoline_park|sauna|spa)$"](area.a);
  nwr["name"]["tourism"~"^(museum|gallery)$"](area.a);
  nwr["name"]["shop"~"^(pastry|confectionery)$"](area.a);
);
out center tags;"""


def overpass():
    for url in SERVIDORES:
        for _ in range(2):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': Q}).encode(), headers={'User-Agent': 'radar-planes-madrid/1.0'})
                with urllib.request.urlopen(req, timeout=700) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print('Overpass falló', url, e); time.sleep(30)
    raise SystemExit('Ningún servidor de Overpass respondió')


def main():
    data = overpass()
    tiles, total = {}, 0
    for el in data.get('elements', []):
        t = el.get('tags', {})
        lat = el.get('lat', (el.get('center') or {}).get('lat')); lon = el.get('lon', (el.get('center') or {}).get('lon'))
        if lat is None or not t.get('name') or t.get('disused:amenity') or t.get('opening_hours') == 'closed': continue
        tags = {k: t[k] for k in KEEP if t.get(k)}
        key = f"{math.floor(lat / TILE_LAT)}_{math.floor(lon / TILE_LON)}"
        tiles.setdefault(key, []).append([round(lat, 6), round(lon, 6), tags]); total += 1
    if total < 10000: raise SystemExit(f'Solo {total} sitios: algo ha ido mal, no se sobrescribe')
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    for k, v in tiles.items():
        (OUT / f'{k}.json').write_text(json.dumps(v, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (OUT / 'index.json').write_text(json.dumps({'generado': time.strftime('%Y-%m-%d'), 'tile': [TILE_LAT, TILE_LON],
                                                'tiles': {k: len(v) for k, v in tiles.items()}, 'total': total},
                                               separators=(',', ':')), encoding='utf-8')
    print(total, 'sitios en', len(tiles), 'trozos')


if __name__ == '__main__':
    main()
