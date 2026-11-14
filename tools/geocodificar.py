"""Sitúa en el mapa los sitios que no tenían coordenadas a partir de su dirección (tools/direcciones_pendientes.json).

Usa Nominatim de OpenStreetMap (gratis, 1 consulta por segundo). Solo toca sitios sin coordenadas
o que siguen en el centro del barrio; marca locSrc='manual' para que ningún proceso los mueva después.
Se ejecuta en GitHub Actions (.github/workflows/geocodificar.yml), que sí tiene acceso a internet.
"""
import json, time, urllib.parse, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ubicar import load_data, http, km  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

def buscar(s):
    q = {'street': s['calle'], 'postalcode': s.get('cp', ''), 'city': s.get('ciudad', 'Madrid'), 'country': 'España',
         'format': 'jsonv2', 'limit': 1, 'addressdetails': 1}
    res = json.loads(http('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(q), timeout=30))
    time.sleep(1.2)
    if not res:   # segundo intento, en texto libre
        res = json.loads(http('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
            {'q': f"{s['calle']}, {s.get('cp', '')} {s.get('ciudad', 'Madrid')}", 'format': 'jsonv2', 'limit': 1, 'countrycodes': 'es'}), timeout=30))
        time.sleep(1.2)
    return res[0] if res else None

def main():
    cfg = json.loads((ROOT / 'tools' / 'direcciones_pendientes.json').read_text(encoding='utf-8'))['sitios']
    lines, i, data = load_data()
    by = {d['n']: d for d in data}
    ok, fallos = [], []
    for n, s in cfg.items():
        d = by.get(n)
        if not d: fallos.append(n + ' (no está en la lista)'); continue
        if d.get('locSrc') == 'manual' and d.get('locationVerified'): continue   # ya situado
        try: r = buscar(s)
        except Exception as ex: fallos.append(f'{n} (error {ex})'); continue
        lat, lon = (float(r['lat']), float(r['lon'])) if r else (None, None)
        if lat is None or km(40.4168, -3.7038, lat, lon) > 45: fallos.append(n + ' (dirección no encontrada)'); continue
        d.update(lat=round(lat, 6), lon=round(lon, 6), addr=s['addr'], locationVerified=True, locSrc='manual', locFuente='direccion')
        ok.append(f'{n}: {lat:.5f}, {lon:.5f}')
    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')
    print('Situados:', len(ok)); print('\n'.join(ok))
    if fallos: print('Sin situar:\n- ' + '\n- '.join(fallos))

if __name__ == '__main__':
    main()
