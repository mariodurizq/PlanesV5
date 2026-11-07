"""Repaso de la lista de sitios: zonas, coordenadas, duplicados y datos que faltan.

- Descarga de OpenStreetMap (gratis) los límites de los 21 distritos de Madrid y de los 179 municipios.
- Para cada sitio con coordenadas calcula en qué distrito/municipio cae de verdad.
- Si la dirección dice otra zona distinta → las coordenadas son sospechosas: se avisa y no se toca.
- Si no, corrige la zona (z) cuando está vacía o es distinta. Nunca borra sitios.
- Escribe tools/revision.md con todo lo que ha visto.
"""
import json, re, sys, time, unicodedata, pathlib, urllib.request, urllib.parse, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ubicar import load_data, km  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVIDORES = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
              'https://overpass.private.coffee/api/interpreter']
Q = """[out:json][timeout:300];
area["ISO3166-2"="ES-MD"]->.a;
relation["boundary"="administrative"]["admin_level"="8"](area.a);
out geom;
area["name"="Madrid"]["boundary"="administrative"]["admin_level"="8"]->.m;
relation["boundary"="administrative"]["admin_level"="9"](area.m);
out geom;"""


def strip(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s*-\s*', '-', re.sub(r'[^a-z0-9 -]+', ' ', s)).strip()


def overpass():
    for url in SERVIDORES:
        for _ in range(2):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': Q}).encode(), headers={'User-Agent': 'radar-planes-madrid/1.0'})
                with urllib.request.urlopen(req, timeout=330) as r:
                    return json.loads(r.read().decode())
            except Exception as e:
                print('Overpass falló', url, e); time.sleep(20)
    raise SystemExit('Ningún servidor de Overpass respondió')


def areas(data):
    out = []
    for el in data.get('elements', []):
        t = el.get('tags', {})
        name = t.get('name:es') or t.get('name')
        if not name: continue
        segs = []
        for m in el.get('members', []):
            g = m.get('geometry')
            if m.get('type') == 'way' and g:
                for a, b in zip(g, g[1:]): segs.append((a['lon'], a['lat'], b['lon'], b['lat']))
        if not segs: continue
        xs = [s[0] for s in segs] + [s[2] for s in segs]; ys = [s[1] for s in segs] + [s[3] for s in segs]
        out.append({'n': name, 'lvl': t.get('admin_level'), 'segs': segs, 'bb': (min(xs), min(ys), max(xs), max(ys))})
    return out


def dentro(lon, lat, a):
    x0, y0, x1, y1 = a['bb']
    if not (x0 <= lon <= x1 and y0 <= lat <= y1): return False
    c = False
    for ax, ay, bx, by in a['segs']:   # paridad del rayo: vale aunque los tramos no estén ordenados
        if (ay > lat) != (by > lat) and lon < ax + (lat - ay) * (bx - ax) / (by - ay): c = not c
    return c


def main():
    lines, i, data = load_data()
    polys = areas(overpass())
    distritos = [a for a in polys if a['lvl'] == '9']
    municipios = [a for a in polys if a['lvl'] == '8']
    print(len(distritos), 'distritos,', len(municipios), 'municipios')
    if len(distritos) < 21 or len(municipios) < 170: raise SystemExit('Límites incompletos: no toco nada')
    nombres = {strip(a['n']): a['n'] for a in distritos + municipios}
    # alias de cómo aparecen en la lista y en las direcciones de Google
    nombres.update({'moncloa-aravaca': next((a['n'] for a in distritos if strip(a['n']).startswith('moncloa')), 'Moncloa-Aravaca'),
                    'fuencarral-el pardo': next((a['n'] for a in distritos if strip(a['n']).startswith('fuencarral')), 'Fuencarral-El Pardo'),
                    'san blas-canillejas': next((a['n'] for a in distritos if strip(a['n']).startswith('san blas')), 'San Blas-Canillejas')})
    zona_lista = {}   # cómo escribe la lista cada zona (para respetar su forma: "Moncloa-Aravaca")
    for d in data:
        if d.get('z'): zona_lista.setdefault(strip(d['z']), d['z'])

    def zona_de(lat, lon):
        mun = next((a for a in municipios if dentro(lon, lat, a)), None)
        if mun and strip(mun['n']) == 'madrid':
            dis = next((a for a in distritos if dentro(lon, lat, a)), None)
            return dis['n'] if dis else 'Madrid'
        return mun['n'] if mun else None

    def zona_direccion(addr):
        if not addr: return None
        partes = [strip(p) for p in str(addr).split(',')]
        for p in partes[1:]:   # la primera parte es la calle
            p = re.sub(r'^\d{5}\s*', '', p).strip()
            if p in nombres and p != 'madrid': return nombres[p]
        return None

    cambios, sospechosas, fuera, sin_coords, vacias_ok = [], [], [], [], 0
    for d in data:
        if not isinstance(d.get('lat'), (int, float)) or not isinstance(d.get('lon'), (int, float)):
            sin_coords.append(d['n']); continue
        real = zona_de(d['lat'], d['lon'])
        if not real:
            fuera.append(f"{d['n']} ({d['lat']:.4f}, {d['lon']:.4f})"); continue
        por_dir = zona_direccion(d.get('addr'))
        if por_dir and strip(por_dir) != strip(real):
            sospechosas.append(f"{d['n']}: la dirección dice **{por_dir}** pero las coordenadas caen en **{real}** — {d.get('addr','')}")
            continue
        actual = d.get('z') or ''
        nuevo = zona_lista.get(strip(real), real)
        if strip(actual) != strip(nuevo):
            cambios.append(f"{d['n']}: {actual or '(sin zona)'} → {nuevo}")
            if not actual: vacias_ok += 1
            d['z'] = nuevo; d['zSrc'] = 'limites-osm'
    # posibles duplicados (mismo nombre, a menos de 150 m)
    dup, vistos = [], {}
    for d in data:
        if not isinstance(d.get('lat'), (int, float)): continue
        k = re.sub(r'[^a-z0-9]', '', strip(d['n']))[:18]
        for o in vistos.get(k, []):
            if km(d['lat'], d['lon'], o['lat'], o['lon']) < 0.15: dup.append(f"{o['n']} / {d['n']}")
        vistos.setdefault(k, []).append(d)
    cerrados = [d['n'] for d in data if d.get('e') == 'Cerrado definitivamente' or d.get('cerradoDesde')]
    sin_cat = [d['n'] for d in data if not d.get('cm')]

    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')

    def bloque(t, xs, lim=400):
        return f"\n## {t} ({len(xs)})\n" + ('\n'.join('- ' + x for x in xs[:lim]) if xs else '- Nada 👍') + '\n'
    md = (f"# Repaso de la lista de sitios — {datetime.date.today().isoformat()}\n\n"
          f"Sitios: **{len(data)}** · zonas corregidas: **{len(cambios)}** (de ellas {vacias_ok} estaban vacías) · "
          f"coordenadas sospechosas: **{len(sospechosas)}** · fuera de la Comunidad: **{len(fuera)}** · sin coordenadas: **{len(sin_coords)}** · "
          f"posibles duplicados: **{len(dup)}** · cerrados: **{len(cerrados)}**\n\n"
          "La zona se calcula con los límites oficiales de distritos y municipios de OpenStreetMap. "
          "Si la dirección dice otra zona, no se toca nada y se apunta aquí para revisarlo a mano.\n"
          + bloque('Zonas corregidas', cambios) + bloque('Coordenadas sospechosas (revisar a mano)', sospechosas)
          + bloque('Fuera de la Comunidad de Madrid', fuera) + bloque('Sin coordenadas', sin_coords)
          + bloque('Posibles duplicados', dup) + bloque('Marcados como cerrados (se ocultan en la web, no se borran)', cerrados)
          + bloque('Sin categoría', sin_cat))
    (ROOT / 'tools' / 'revision.md').write_text(md, encoding='utf-8')
    print(md[:1500])


if __name__ == '__main__':
    main()
