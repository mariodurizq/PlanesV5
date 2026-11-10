"""Mete en la lista los «Sitios que rentan» (tools/sitios_que_rentan.json).

Los que ya estaban se marcan (mr=1) sin tocar su ubicación; los nuevos se añaden con coordenadas
manuales (locSrc='manual', así ningún proceso automático los mueve). Se puede ejecutar las veces que haga falta.
"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from ubicar import load_data  # noqa: E402

def main():
    cfg = json.loads((ROOT / 'tools' / 'sitios_que_rentan.json').read_text(encoding='utf-8'))
    lines, i, data = load_data()
    by = {d['n']: d for d in data}
    nuevos = marcados = 0
    for orden, s in enumerate(cfg['sitios']):
        if s.get('existe'):
            d = by.get(s['existe'])
            if not d: print('NO ENCONTRADO', s['existe']); continue
            marcados += 1
        else:
            d = by.get(s['n'])
            if not d:
                d = {'n': s['n'], 'e': 'Abierto'}; data.append(d); by[s['n']] = d; nuevos += 1
            for k in ('cm', 'cd', 'z', 'p', 'addr', 'web', 'oh'):
                if s.get(k): d[k] = s[k]
            d.update(lat=s['lat'], lon=s['lon'], locationVerified=True, locSrc='manual')
            if s.get('aprox'): d['locAprox'] = True
        for k in ('cm', 'cd'):
            if s.get('existe') and s.get(k): d[k] = s[k]
        d['mr'] = 1; d['marca'] = s['marca']; d['sede'] = s['sede']; d['mro'] = orden
    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Sitios que rentan: {nuevos} nuevos, {marcados} ya estaban; total en la lista {len(data)}')

if __name__ == '__main__':
    main()
