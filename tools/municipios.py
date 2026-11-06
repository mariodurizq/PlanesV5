"""Genera municipios.json: los 179 municipios de la Comunidad de Madrid con su centro y población.

Fuente: OpenStreetMap (Overpass), gratis. Se ejecuta a mano o una vez al año; los municipios casi no cambian.
"""
import json, time, pathlib, urllib.request, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVIDORES = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
              'https://overpass.private.coffee/api/interpreter']
Q = '[out:json][timeout:120];area["ISO3166-2"="ES-MD"]->.a;relation["boundary"="administrative"]["admin_level"="8"](area.a);out center tags;'


def overpass():
    for url in SERVIDORES:
        for intento in range(2):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': Q}).encode(),
                                             headers={'User-Agent': 'radar-planes-madrid/1.0'})
                with urllib.request.urlopen(req, timeout=150) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print('Overpass falló', url, e); time.sleep(10)
    raise SystemExit('Ningún servidor de Overpass respondió')


def radio(pop):
    if pop >= 150000: return 5.0
    if pop >= 50000: return 3.5
    if pop >= 15000: return 2.5
    if pop >= 3000: return 2.0
    return 1.5


def main():
    data = overpass()
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {}); c = el.get('center') or {}
        name = t.get('name:es') or t.get('name')
        if not name or not c: continue
        try: pop = int(str(t.get('population', '0')).replace('.', '').replace(' ', '') or 0)
        except ValueError: pop = 0
        out.append({'n': name, 'lat': round(c['lat'], 5), 'lon': round(c['lon'], 5), 'pop': pop, 'r': radio(pop),
                    'ine': t.get('ine:municipio') or t.get('ref:ine') or ''})
    out.sort(key=lambda m: -m['pop'])
    if len(out) < 170: raise SystemExit(f'Solo {len(out)} municipios: algo ha ido mal, no se sobrescribe')
    (ROOT / 'municipios.json').write_text(json.dumps({'generado': time.strftime('%Y-%m-%d'), 'municipios': out},
                                                     ensure_ascii=False, indent=0), encoding='utf-8')
    print(len(out), 'municipios guardados')


if __name__ == '__main__':
    main()
