"""Descubre sitios nuevos muy bien valorados en Google que aún no están en tu lista → nuevos.json.

Se ejecuta una vez al mes (GitHub Actions). Unas 65 consultas al mes: 13 tipos × 5 zonas.
Criterio: nota ≥ 4,5 con al menos 200 reseñas, abierto, y que no esté ya en tu lista.
"""
import json, re, sys, math, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from google_util import places, CALLS, KEY
from ubicar import sim, norm, load_data

ROOT = pathlib.Path(__file__).resolve().parent.parent
TIPOS = [('sushi', 'Asiática', 'Japonesa/Sushi'), ('ramen', 'Asiática', 'Ramen'), ('restaurante italiano', 'Italiana/Pizza', 'Italiana'),
         ('pizzería napolitana', 'Italiana/Pizza', 'Pizza napolitana'), ('hamburguesería', 'Hamburguesas', 'Hamburguesas'),
         ('restaurante mexicano', 'Mexicana', 'Mexicana'), ('asador argentino', 'Carnes/Parrilla', 'Argentina/Parrilla'),
         ('bar de tapas', 'Española/Mediterránea', 'Tapas'), ('brunch', 'Café/Brunch/Postres', 'Brunch'),
         ('cafetería de especialidad', 'Café/Brunch/Postres', 'Café de especialidad'), ('coctelería', 'Coctelería', 'Coctelería'),
         ('rooftop bar', 'Rooftop/Terraza', 'Rooftop'), ('restaurante peruano', 'Restaurante (general)', 'Peruana')]
ZONAS = [('Centro', 40.4168, -3.7038), ('Malasaña', 40.4262, -3.7045), ('Chamberí', 40.4340, -3.7030),
         ('Salamanca', 40.4300, -3.6800), ('Lavapiés', 40.4087, -3.7010)]
FIELDS = 'places.id,places.displayName,places.location,places.formattedAddress,places.rating,places.userRatingCount,places.businessStatus,places.priceLevel'
PRICE = {'PRICE_LEVEL_INEXPENSIVE': '1-15', 'PRICE_LEVEL_MODERATE': '15-30', 'PRICE_LEVEL_EXPENSIVE': '30-50', 'PRICE_LEVEL_VERY_EXPENSIVE': '50+'}

def main():
    if not KEY: raise SystemExit('Falta GOOGLE_PLACES_KEY')
    _, _, data = load_data()
    known = [d['n'] for d in data]
    found = {}
    for q, cm, cd in TIPOS:
        for zona, lat, lon in ZONAS:
            res = places('searchText', {'textQuery': f'{q} en {zona}, Madrid', 'maxResultCount': 20, 'languageCode': 'es',
                                        'locationBias': {'circle': {'center': {'latitude': lat, 'longitude': lon}, 'radius': 1500.0}}}, FIELDS)
            for p in res:
                name = (p.get('displayName') or {}).get('text', '')
                r, n = p.get('rating') or 0, p.get('userRatingCount') or 0
                if not name or p.get('businessStatus') not in (None, 'OPERATIONAL') or r < 4.5 or n < 200: continue
                if any(sim(name, k) >= .85 for k in known): continue
                loc = p.get('location') or {}
                score = (r * n + 4.3 * 300) / (n + 300)   # nota ajustada por número de reseñas
                prev = found.get(p['id'])
                if prev and prev['_score'] >= score: continue
                found[p['id']] = {'n': name, 'cm': cm, 'cd': cd, 'z': zona, 'e': 'Abierto', 'v': r, 'nr': n,
                                  'p': PRICE.get(p.get('priceLevel'), ''), 'lat': round(loc.get('latitude', 0), 6), 'lon': round(loc.get('longitude', 0), 6),
                                  'addr': (p.get('formattedAddress') or '').split(', Madrid')[0], 'locationVerified': True, 'nuevo': True,
                                  'no': f'Descubierto por sus reseñas ({r} ★, {n} opiniones).', '_score': round(score, 3)}
    if not CALLS['n']:
        print('Google no disponible este mes (tope gratuito): se mantiene nuevos.json tal cual.'); return
    out = sorted(found.values(), key=lambda x: -x['_score'])[:120]
    for x in out: x.pop('_score', None)
    (ROOT / 'nuevos.json').write_text(json.dumps({'actualizado': datetime.date.today().isoformat(), 'criterio': '≥4,5 ★ y ≥200 reseñas', 'sitios': out}, ensure_ascii=False), encoding='utf-8')
    print(len(out), 'sitios nuevos ·', CALLS['n'], 'consultas a Google')

if __name__ == '__main__':
    main()
