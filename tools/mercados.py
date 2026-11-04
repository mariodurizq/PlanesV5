"""Mercados gastronómicos de Madrid y sus puestos de comida → mercados.json.

Mensual en GitHub Actions. Solo usa la tarifa básica de Google («Pro», con tope mensual, ~40 consultas):
1) Busca los mercados (lista base + búsquedas de Google).
2) Para cada mercado, pide a Google los locales de comida a menos de 45 m (los puestos).
3) Clasifica cada puesto por tipo de comida.
"""
import json, re, sys, math, datetime, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from google_util import places, KEY, CALLS
from ubicar import sim, km, norm

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ['Mercado de San Miguel', 'Mercado de San Antón', 'Mercado de Antón Martín', 'Mercado de San Ildefonso', 'Mercado de la Paz',
        'Mercado de Vallehermoso', 'Mercado de Chamberí', 'Mercado de Barceló', 'Mercado de los Mostenses', 'Mercado de San Fernando',
        'Mercado de la Cebada', 'Mercado de Chamartín', 'Mercado de Prosperidad', 'Mercado de Maravillas', 'Mercado de Guzmán el Bueno',
        'Mercado de Ibiza', 'Mercado de Santa María de la Cabeza', 'Mercado de Tirso de Molina', 'Mercado de la Reina',
        'Mercado de Moncloa', 'Mercado de San Enrique', 'Mercado de Argüelles', 'Mercado de Torrijos', 'Mercado de Diego de León',
        'Mercado de Pacífico', 'Mercado de Usera', 'Mercado de Tetuán', 'Mercado de la Guindalera']
TIPO = {'japanese_restaurant': 'Japonesa', 'sushi_restaurant': 'Sushi', 'ramen_restaurant': 'Ramen', 'seafood_restaurant': 'Marisco y pescado',
        'spanish_restaurant': 'Española', 'tapas_restaurant': 'Tapas', 'italian_restaurant': 'Italiana', 'pizza_restaurant': 'Pizza',
        'mexican_restaurant': 'Mexicana', 'hamburger_restaurant': 'Hamburguesas', 'steak_house': 'Carnes', 'barbecue_restaurant': 'Brasa',
        'chinese_restaurant': 'China', 'korean_restaurant': 'Coreana', 'thai_restaurant': 'Tailandesa', 'vietnamese_restaurant': 'Vietnamita',
        'indian_restaurant': 'India', 'middle_eastern_restaurant': 'Oriente Medio', 'lebanese_restaurant': 'Libanesa', 'turkish_restaurant': 'Turca',
        'greek_restaurant': 'Griega', 'mediterranean_restaurant': 'Mediterránea', 'french_restaurant': 'Francesa', 'peruvian_restaurant': 'Peruana',
        'argentinian_restaurant': 'Argentina', 'brazilian_restaurant': 'Brasileña', 'vegan_restaurant': 'Vegana', 'vegetarian_restaurant': 'Vegetariana',
        'brunch_restaurant': 'Brunch', 'breakfast_restaurant': 'Desayunos', 'sandwich_shop': 'Bocadillos', 'cafe': 'Café', 'coffee_shop': 'Café',
        'bakery': 'Panadería y dulces', 'dessert_shop': 'Postres', 'confectionery': 'Dulces', 'ice_cream_shop': 'Helados', 'wine_bar': 'Vinos',
        'bar': 'Bar', 'pub': 'Bar', 'cocktail_bar': 'Cócteles', 'fast_food_restaurant': 'Comida rápida', 'meal_takeaway': 'Para llevar',
        'deli': 'Charcutería y gourmet', 'asian_restaurant': 'Asiática', 'african_restaurant': 'Africana', 'restaurant': 'Restaurante'}
PALABRAS = [(r'ostra|marisc|pescad|pulpo|boquer|crab|cangrej|gamba|lobster|bacalao|anchoa', 'Marisco y pescado'), (r'spritz|cocktail|c[oó]ctel', 'Cócteles'), (r'jam[oó]n|ib[eé]ric|embutid|charcut', 'Charcutería y gourmet'),
            (r'queso|quesos|fromag', 'Quesos'), (r'croquet', 'Croquetas'), (r'sushi|japo|nikkei|izakaya', 'Japonesa'), (r'pizza', 'Pizza'),
            (r'pasta|trattoria', 'Italiana'), (r'taco|mexic', 'Mexicana'), (r'burger|hamburg', 'Hamburguesas'), (r'vino|vermut|bodega', 'Vinos'),
            (r'cervez|beer', 'Cervezas'), (r'empanad|argentin', 'Argentina'), (r'ceviche|peru', 'Peruana'), (r'dulce|pastel|chocolat|churr|postre', 'Dulces'),
            (r'caf[eé]|coffee', 'Café'), (r'paella|arroz', 'Arroces'), (r'frut|verdur', 'Fruta y verdura'), (r'carne|asador|parrill|brasa', 'Carnes')]

def basura(name, mercado):
    """Fichas que no son puestos: textos raros, la propia ficha del mercado, aparcamientos…"""
    if re.search(r'[•#]|\d{1,3}[.,]\d{3}|parking|aparcamiento|farmacia|banco|cajero', name, re.I): return True
    return bool(re.search(r'\bmercado\b', name, re.I) and len(name) > 45)

def tipo(p):
    name = (p.get('displayName') or {}).get('text', '')
    for rx, t in PALABRAS:
        if re.search(rx, name, re.I): return t
    pt = p.get('primaryType') or ''
    if pt in TIPO and pt != 'restaurant': return TIPO[pt]
    for t in p.get('types') or []:
        if t in TIPO and t != 'restaurant': return TIPO[t]
    return TIPO.get(pt, 'Comida')

def main():
    if not KEY: raise SystemExit('Falta GOOGLE_PLACES_KEY')
    cands = {}
    queries = BASE + ['mercado gastronómico Madrid', 'mercado de abastos con barra de degustación Madrid', 'food hall Madrid']
    for q in queries:
        for p in places('searchText', {'textQuery': q if 'Madrid' in q else q + ', Madrid', 'maxResultCount': 5 if q in BASE else 20, 'languageCode': 'es',
                                       'locationBias': {'circle': {'center': {'latitude': 40.4168, 'longitude': -3.7038}, 'radius': 15000.0}}},
                        'places.id,places.displayName,places.location,places.formattedAddress,places.types,places.businessStatus'):
            name = (p.get('displayName') or {}).get('text', ''); loc = p.get('location') or {}
            if p.get('businessStatus') not in (None, 'OPERATIONAL') or 'latitude' not in loc: continue
            if not re.search(r'mercado|market|food hall|galer[ií]a gastron', name, re.I): continue
            if q in BASE and sim(q, name) < .7: continue
            if km(40.4168, -3.7038, loc['latitude'], loc['longitude']) > 15: continue
            cands[p['id']] = {'n': name, 'lat': round(loc['latitude'], 6), 'lon': round(loc['longitude'], 6), 'addr': (p.get('formattedAddress') or '').split(', Madrid')[0]}
    # quita duplicados del mismo mercado (dos fichas a <60 m)
    mercados = []
    for m in cands.values():
        if any(km(m['lat'], m['lon'], o['lat'], o['lon']) < .06 for o in mercados): continue
        mercados.append(m)
    print(len(mercados), 'mercados candidatos')
    out = []
    for m in mercados:
        res = places('searchNearby', {'includedTypes': ['restaurant', 'bar', 'cafe', 'bakery', 'meal_takeaway', 'ice_cream_shop'],
                                       'maxResultCount': 20, 'languageCode': 'es', 'rankPreference': 'DISTANCE',
                                       'locationRestriction': {'circle': {'center': {'latitude': m['lat'], 'longitude': m['lon']}, 'radius': 45.0}}},
                     'places.id,places.displayName,places.location,places.types,places.primaryType,places.businessStatus')
        puestos = []
        for p in res:
            name = (p.get('displayName') or {}).get('text', '')
            if not name or p.get('businessStatus') not in (None, 'OPERATIONAL') or sim(name, m['n']) > .8 or basura(name, m['n']): continue
            loc = p.get('location') or {}
            puestos.append({'n': re.sub(r'\s*[-–|·]\s*(mercado|market).*$', '', name, flags=re.I).strip(), 'tipo': tipo(p),
                            'lat': round(loc.get('latitude', 0), 6) or None, 'lon': round(loc.get('longitude', 0), 6) or None})
        if len(puestos) >= 3:
            m['puestos'] = sorted(puestos, key=lambda x: (x['tipo'], x['n']))
            m['tipos'] = sorted({x['tipo'] for x in puestos})
            out.append(m)
    if not CALLS['n']: raise SystemExit('Sin consultas a Google (tope o clave): no se toca mercados.json')
    out.sort(key=lambda m: -len(m['puestos']))
    (ROOT / 'mercados.json').write_text(json.dumps({'actualizado': datetime.date.today().isoformat(), 'mercados': out}, ensure_ascii=False), encoding='utf-8')
    print(len(out), 'mercados con puestos ·', sum(len(m['puestos']) for m in out), 'puestos ·', CALLS['n'], 'consultas')

if __name__ == '__main__':
    main()
