"""Cada lunes: restaurantes, coctelerías y shishas de la Comunidad de Madrid con ≥400 reseñas y nota ≥4,8 en Google.

Resultado en nuevos.json (se acumula: lo encontrado en semanas anteriores se mantiene y se actualiza).
~150 consultas por ejecución a la tarifa «Enterprise» de Google, con tope mensual por debajo de lo gratuito.
"""
import json, re, sys, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from google_util import places, CALLS, KEY, disponible
from ubicar import sim, load_data, km

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIN_RESENAS, MIN_NOTA = 400, 4.8
ZONAS = [  # (nombre, lat, lon, radio m, páginas para restaurantes)
    ('Centro', 40.4165, -3.7050, 1500, 3), ('Chamberí', 40.4360, -3.7040, 1400, 2), ('Salamanca', 40.4300, -3.6790, 1500, 3),
    ('Retiro', 40.4120, -3.6800, 1500, 2), ('Arganzuela', 40.3980, -3.7000, 1600, 1), ('Moncloa', 40.4352, -3.7190, 2000, 2),
    ('Chamartín', 40.4580, -3.6770, 1800, 2), ('Tetuán', 40.4600, -3.6990, 1500, 1), ('Fuencarral', 40.4970, -3.7160, 4000, 1),
    ('Latina', 40.3990, -3.7560, 2500, 1), ('Carabanchel', 40.3830, -3.7280, 2500, 1), ('Usera', 40.3830, -3.7060, 1800, 1),
    ('Puente de Vallecas', 40.3920, -3.6650, 2000, 1), ('Villa de Vallecas', 40.3730, -3.6200, 2500, 1), ('Moratalaz', 40.4070, -3.6440, 1800, 1),
    ('Ciudad Lineal', 40.4460, -3.6520, 2200, 1), ('Hortaleza', 40.4730, -3.6410, 2500, 1), ('Villaverde', 40.3460, -3.7000, 2500, 1),
    ('Vicálvaro', 40.4040, -3.6080, 2500, 1), ('San Blas', 40.4300, -3.6120, 2500, 1), ('Barajas', 40.4730, -3.5800, 2500, 1),
    ('Alcobendas', 40.5373, -3.6372, 3500, 1), ('San Sebastián de los Reyes', 40.5473, -3.6260, 3000, 1), ('Tres Cantos', 40.6007, -3.7096, 3000, 1),
    ('Las Rozas', 40.4930, -3.8737, 4000, 1), ('Majadahonda', 40.4733, -3.8724, 3000, 1), ('Pozuelo de Alarcón', 40.4350, -3.8135, 3500, 1),
    ('Boadilla del Monte', 40.4053, -3.8750, 3500, 1), ('Alcorcón', 40.3459, -3.8245, 3000, 1), ('Leganés', 40.3283, -3.7635, 3000, 1),
    ('Getafe', 40.3082, -3.7324, 3500, 1), ('Fuenlabrada', 40.2842, -3.7942, 3000, 1), ('Móstoles', 40.3228, -3.8650, 3000, 1),
    ('Parla', 40.2378, -3.7740, 3000, 1), ('Pinto y Valdemoro', 40.2150, -3.6850, 4500, 1), ('Rivas-Vaciamadrid', 40.3530, -3.5390, 3500, 1),
    ('Coslada y San Fernando', 40.4240, -3.5470, 3500, 1), ('Torrejón de Ardoz', 40.4600, -3.4800, 3500, 1), ('Alcalá de Henares', 40.4818, -3.3641, 4500, 1),
    ('Arganda del Rey', 40.3008, -3.4382, 4000, 1), ('Collado Villalba y Torrelodones', 40.6060, -3.9660, 6000, 1),
    ('Sierra de Guadarrama', 40.7300, -4.0300, 9000, 1), ('Colmenar Viejo', 40.6590, -3.7660, 4000, 1), ('Aranjuez y Chinchón', 40.0850, -3.5150, 9000, 1),
    ('San Lorenzo de El Escorial', 40.5920, -4.1470, 5000, 1), ('Sierra Norte', 40.9300, -3.6800, 15000, 1), ('Navalcarnero y Villaviciosa', 40.3220, -3.9560, 6000, 1),
]
TIPOS = [('restaurante', 'restaurantes'), ('cocteleria', 'coctelería'), ('shisha', 'shisha cachimba lounge')]
FIELDS = 'places.id,places.displayName,places.location,places.formattedAddress,places.rating,places.userRatingCount,places.businessStatus,places.priceLevel,places.primaryType,places.types,nextPageToken'
PRICE = {'PRICE_LEVEL_INEXPENSIVE': '1-15', 'PRICE_LEVEL_MODERATE': '15-30', 'PRICE_LEVEL_EXPENSIVE': '30-50', 'PRICE_LEVEL_VERY_EXPENSIVE': '50+'}
COCINA = [  # (tipo de Google, categoría de la app, texto)
    (r'sushi|japanese|ramen', 'Asiática', 'Japonesa'), (r'chinese|dim_sum', 'Asiática', 'China'), (r'korean', 'Asiática', 'Coreana'),
    (r'thai|vietnamese|asian|indonesian', 'Asiática', 'Asiática'), (r'italian|pizza', 'Italiana/Pizza', 'Italiana'),
    (r'mexican', 'Mexicana', 'Mexicana'), (r'hamburger', 'Hamburguesas', 'Hamburguesas'),
    (r'steak|barbecue|argentin|brazilian', 'Carnes/Parrilla', 'Carnes/Parrilla'), (r'seafood', 'Española/Mediterránea', 'Marisquería'),
    (r'spanish|tapas|mediterranean|basque', 'Española/Mediterránea', 'Española'), (r'indian|pakistani|nepal', 'Restaurante (general)', 'India'),
    (r'peruvian', 'Restaurante (general)', 'Peruana'), (r'lebanese|middle_eastern|turkish|greek|moroccan', 'Restaurante (general)', 'Mediterránea oriental'),
    (r'vegan|vegetarian', 'Restaurante (general)', 'Vegana/Vegetariana'), (r'brunch|breakfast|cafe|coffee|bakery|dessert', 'Café/Brunch/Postres', 'Brunch/Café'),
]

def categoria(tipo, p):
    name = (p.get('displayName') or {}).get('text', '')
    ts = ' '.join([p.get('primaryType') or ''] + (p.get('types') or []))
    if tipo == 'shisha' or re.search(r'shisha|cachimba|hookah|narguil', name, re.I) or 'hookah' in ts: return 'Shisha Lounge', 'Shisha'
    if tipo == 'cocteleria' or re.search(r'cocktail|bar\b', p.get('primaryType') or ''): return 'Coctelería', 'Coctelería'
    for rx, cm, cd in COCINA:
        if re.search(rx, ts): return cm, cd
    return 'Restaurante (general)', 'Restaurante'

def valido(tipo, p):
    ts = ' '.join([p.get('primaryType') or ''] + (p.get('types') or []))
    name = (p.get('displayName') or {}).get('text', '')
    if tipo == 'shisha': return bool(re.search(r'shisha|cachimba|hookah|narguil|lounge|tea', name + ' ' + ts, re.I))
    if tipo == 'cocteleria': return bool(re.search(r'bar|pub|night_club|cocktail|lounge', ts))
    return bool(re.search(r'restaurant|food|meal|cafe|bakery|brunch', ts))

def main():
    if not KEY: raise SystemExit('Falta GOOGLE_PLACES_KEY')
    if not disponible('enterprise', 140):
        print('No queda cupo gratuito de Google este mes para la búsqueda semanal: se mantiene nuevos.json.'); return
    _, _, data = load_data(); mios = [d['n'] for d in data]
    path = ROOT / 'nuevos.json'
    prev = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'sitios': []}
    por_id = {s['gid']: s for s in prev.get('sitios', []) if s.get('gid')}
    hoy = datetime.date.today().isoformat(); vistos = set()
    for zona, lat, lon, radio, paginas in ZONAS:
        for tipo, q in TIPOS:
            token = None
            for pag in range(paginas if tipo == 'restaurante' else 1):
                body = {'textQuery': f'{q} en {zona}, Madrid', 'pageSize': 20, 'languageCode': 'es', 'minRating': 4.5,
                        'locationBias': {'circle': {'center': {'latitude': lat, 'longitude': lon}, 'radius': float(radio)}}}
                if token: body['pageToken'] = token
                resp = places('searchText', body, FIELDS, full=True)
                res = resp.get('places', [])
                for p in res:
                    r, n = p.get('rating') or 0, p.get('userRatingCount') or 0
                    loc = p.get('location') or {}
                    if r < MIN_NOTA or n < MIN_RESENAS or p.get('businessStatus') not in (None, 'OPERATIONAL') or 'latitude' not in loc: continue
                    if km(40.4168, -3.7038, loc['latitude'], loc['longitude']) > 90 or not valido(tipo, p): continue
                    name = (p.get('displayName') or {}).get('text', '')
                    if any(sim(name, m) >= .85 for m in mios): continue
                    cm, cd = categoria(tipo, p)
                    vistos.add(p['id'])
                    s = por_id.get(p['id'], {'gid': p['id'], 'desde': hoy})
                    s.update({'n': name, 'cm': cm, 'cd': cd, 'z': zona, 'e': 'Abierto', 'v': r, 'nr': n, 'p': PRICE.get(p.get('priceLevel'), s.get('p', '')),
                              'lat': round(loc['latitude'], 6), 'lon': round(loc['longitude'], 6), 'addr': (p.get('formattedAddress') or '').split(', España')[0],
                              'locationVerified': True, 'nuevo': True, 'visto': hoy,
                              'no': f'Añadido automáticamente: {r} ★ con {n} reseñas en Google.'})
                    por_id[p['id']] = s
                token = resp.get('nextPageToken')
                if not token: break
    if not CALLS['n']:
        print('Google no respondió: no se toca nuevos.json'); return
    # Se quitan los que llevan 8 semanas sin aparecer (cerrados o que bajaron de nota)
    limite = (datetime.date.today() - datetime.timedelta(weeks=8)).isoformat()
    sitios = sorted((s for s in por_id.values() if s.get('visto', hoy) >= limite), key=lambda s: (-s['v'], -s['nr']))
    path.write_text(json.dumps({'actualizado': hoy, 'criterio': f'≥{MIN_NOTA} ★ y ≥{MIN_RESENAS} reseñas en Google · Comunidad de Madrid', 'sitios': sitios}, ensure_ascii=False), encoding='utf-8')
    nuevos = sum(1 for s in sitios if s.get('desde') == hoy)
    print(f'{len(sitios)} sitios en total · {nuevos} nuevos esta semana · {CALLS["n"]} consultas a Google')

if __name__ == '__main__':
    main()
