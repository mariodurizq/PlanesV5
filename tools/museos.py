"""Genera museos.json: todos los museos de la Comunidad de Madrid para la capa 🏛️ del mapa.

Une los de OpenStreetMap (carpeta osm/, tourism=museum) con los museos que haya en la lista de Me Renta Mazo.
Solo se muestran datos que vienen de la fuente (dirección, horario, web): nada de precios inventados.
"""
import json, re, sys, glob, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '_site')
sys.path.insert(0, str(ROOT / 'tools'))
from ubicar import load_data, km  # noqa: E402

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()

def main():
    _, _, data = load_data()
    out = []
    def add(n, lat, lon, addr='', web='', oh='', ciudad='', lista=False):
        k = norm(n)
        if not k: return
        for o in out:
            d = km(lat, lon, o['la'], o['lo'])
            if (d < 0.3 and (norm(o['n']) == k or norm(o['n']) in k or k in norm(o['n']))) or d < 0.02:
                o['a'] = o['a'] or addr; o['w'] = o['w'] or web; o['h'] = o['h'] or oh; o['l'] = o['l'] or (1 if lista else 0)
                return
        out.append({'n': n, 'la': round(lat, 5), 'lo': round(lon, 5), 'a': addr, 'w': web, 'h': oh, 'c': ciudad, 'l': 1 if lista else 0})
    for d in data:   # los museos de tu lista primero
        if not isinstance(d.get('lat'), (int, float)) or d.get('e') == 'Cerrado definitivamente': continue
        if re.search(r'\bmuseo\b|\bmuseum\b', d['n'], re.I) or re.search(r'\bmuseo\b', d.get('cd') or '', re.I):
            add(d['n'], d['lat'], d['lon'], (d.get('addr') or '').replace(', España', ''), d.get('web') or '', d.get('oh') or '', '', True)
    for f in glob.glob(str(ROOT / 'osm' / '*_*.json')):
        for lat, lon, t in json.loads(pathlib.Path(f).read_text(encoding='utf-8')):
            if t.get('tourism') != 'museum' or not t.get('name'): continue
            addr = ' '.join(x for x in [t.get('addr:street', ''), t.get('addr:housenumber', '')] if x)
            ciudad = t.get('addr:city', '')
            if ciudad and addr: addr += ', ' + ciudad
            add(t['name'], lat, lon, addr, t.get('website') or t.get('contact:website') or '', t.get('opening_hours') or '', ciudad)
    out.sort(key=lambda o: (-o['l'], o['n'].lower()))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / 'museos.json').write_text(json.dumps({'museos': out}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'museos.json: {len(out)} museos ({sum(o["l"] for o in out)} de tu lista)')

if __name__ == '__main__':
    main()
