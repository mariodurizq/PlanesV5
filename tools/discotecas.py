"""Genera discotecas.json: todas las discotecas de la Comunidad para la capa 🪩 del mapa.

Une las de OpenStreetMap (carpeta osm/) con las de la lista de RENTA. El precio de entrada y de la copa
solo aparece si está apuntado a mano, con su fuente, en tools/discotecas_precios.json: nunca se inventa.
"""
import json, re, sys, glob, pathlib, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '_site')
sys.path.insert(0, str(ROOT / 'tools'))
from ubicar import load_data, km  # noqa: E402

NO_DISCO = re.compile(r'private club|show ?girls?|strip|sauna|swinger|liberal|alterne|whisker|night ?club de|sex|erotic|cabaret lounge', re.I)


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()


def main():
    cfg = json.loads((ROOT / 'tools' / 'discotecas_precios.json').read_text(encoding='utf-8'))
    cerradas = [norm(x) for x in cfg.get('cerradas', [])]
    excluir = [norm(x) for x in cfg.get('excluir', [])]
    _, _, data = load_data()
    out = []

    def add(n, lat, lon, addr='', web='', oh='', lista=False, tipo=''):
        k = norm(n)
        if not k or NO_DISCO.search(n) or any(c in k for c in cerradas) or k in excluir: return
        for o in out:   # mismo sitio: mismo nombre a < 300 m, o nombres casi iguales a < 80 m
            d = km(lat, lon, o['la'], o['lo'])
            if (d < 0.3 and (norm(o['n']) == k or norm(o['n']) in k or k in norm(o['n']))) or d < 0.03:
                o['a'] = o['a'] or addr; o['w'] = o['w'] or web; o['h'] = o['h'] or oh; o['l'] = o['l'] or (1 if lista else 0)
                return
        out.append({'n': n, 'la': round(lat, 5), 'lo': round(lon, 5), 'a': addr, 'w': web, 'h': oh, 'l': 1 if lista else 0, 't': tipo})

    for d in data:   # primero las de la lista (mandan su nombre y su web)
        if d.get('cm') != 'Discoteca/Club' or not isinstance(d.get('lat'), (int, float)): continue
        if d.get('e') == 'Cerrado definitivamente' or d.get('cerradoDesde'): cerradas.append(norm(d['n'])); continue
        if re.search(r'negativ|evitar|no recomend', d.get('no') or '', re.I): continue
        add(d['n'], d['lat'], d['lon'], (d.get('addr') or '').replace(', España', ''), d.get('web') or '', d.get('oh') or '', True, d.get('cd') or '')
    for f in glob.glob(str(ROOT / 'osm' / '*_*.json')):
        for lat, lon, t in json.loads(pathlib.Path(f).read_text(encoding='utf-8')):
            if t.get('amenity') != 'nightclub': continue
            addr = ' '.join(x for x in [t.get('addr:street', ''), t.get('addr:housenumber', '')] if x)
            if t.get('addr:city') and addr: addr += ', ' + t['addr:city']
            add(t['name'], lat, lon, addr, t.get('website') or t.get('contact:website') or '', t.get('opening_hours') or '')
    con = 0
    for p in cfg.get('precios', []):
        keys = [norm(p['n'])] + [norm(a) for a in p.get('alias', [])]
        for o in out:
            k = norm(o['n'])
            if any(x == k or re.search(r'\b' + re.escape(x) + r'\b', k) for x in keys):
                if p.get('entrada'): o['e'] = p['entrada']
                if p.get('copa'): o['c'] = p['copa']
                if p.get('lat'): o['la'], o['lo'] = p['lat'], p['lon']   # la sesión se ha mudado de sala
                if p.get('addr'): o['a'] = p['addr']
                o['f'] = p.get('fuente', ''); o['fd'] = p.get('fecha', ''); con += 1
    out.sort(key=lambda o: (-o['l'], o['n'].lower()))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / 'discotecas.json').write_text(json.dumps({'discotecas': out}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'discotecas.json: {len(out)} discotecas ({sum(o["l"] for o in out)} de la lista, {con} con precio comprobado)')


if __name__ == '__main__':
    main()
