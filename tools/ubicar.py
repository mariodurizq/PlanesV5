"""Ubica los sitios de la app con coordenadas reales y los guarda dentro de index.html.

Se ejecuta en GitHub Actions (.github/workflows/ubicar.yml), que sí tiene acceso a internet.
1) Descarga de OpenStreetMap (Overpass) los locales con nombre de la zona del catálogo.
2) Empareja cada sitio por nombre cerca de su barrio.
3) Los que no salen, los busca uno a uno en Nominatim (1 petición por segundo).
4) Escribe lat/lon reales, horario (oh), tipo de cocina (osmCuisine) y marca locationVerified.
Resumen en tools/ultima_ubicacion.txt. Solo usa la librería estándar de Python.
"""
import json, re, sys, time, math, unicodedata, urllib.request, urllib.parse, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = 'RENTA-planes-madrid/1.0 (github.com/mariodurizq/PlanesV5)'
OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter', 'https://overpass.private.coffee/api/interpreter']
STOP = set('restaurante restaurant bar cafe cafeteria taberna madrid the el la los las de del y and sl by en al meson cerveceria coctel cocteleria pizzeria club lounge shisha'.split())

def strip(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '').lower()) if unicodedata.category(c) != 'Mn')
def norm(n):
    n = re.split(r'\s[-–|·]\s', str(n))[0]
    n = strip(n).replace('&', ' y ')
    n = re.sub(r"['’`´]", '', n)
    return re.sub(r'[^a-z0-9ñ]+', ' ', n).strip()
def tokens(n):
    t = [w for w in norm(n).split() if w]
    c = [w for w in t if w not in STOP]
    return c or t
def branch(n):
    m = re.split(r'\s[-–|·]\s', str(n))
    return norm(' '.join(m[1:])) if len(m) > 1 else ''
def bigrams(s):
    s = ' ' + s + ' '; b = {}
    for i in range(len(s) - 1): b[s[i:i+2]] = b.get(s[i:i+2], 0) + 1
    return b
def dice(a, b):
    if a == b: return 1.0
    A, B = bigrams(a), bigrams(b)
    inter = sum(min(v, B.get(k, 0)) for k, v in A.items())
    tot = sum(A.values()) + sum(B.values())
    return 2 * inter / tot if tot else 0.0
def sim(a, b):
    ba, bb = branch(a), branch(b)
    if ba and bb and dice(ba, bb) < .6: return .5
    ta, tb = tokens(a), tokens(b); ja, jb = ' '.join(ta), ' '.join(tb)
    if not ja or not jb: return 0
    if ja == jb: return 1
    sh, lo = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if all(w in lo for w in sh) and (len(sh) >= 2 or len(sh[0]) >= 7):
        return max(.88 - .04 * (len(lo) - len(sh)), .8)
    return min(dice(ja, jb), dice(norm(a), norm(b)) + .05)
def km(a, b, c, d):
    R = 6371; x = math.radians(c - a); y = math.radians(d - b)
    h = math.sin(x/2)**2 + math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.sin(y/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def http(url, data=None, timeout=200):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8')

def load_data():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    lines = html.split('\n')
    i = next(k for k, l in enumerate(lines) if l.strip().startswith('const DATA = ['))
    data = json.loads(re.sub(r'^\s*const DATA = ', '', lines[i]).rstrip().rstrip(';'))
    return lines, i, data

def overpass_pois(data, csv_text=None):
    pts = [d for d in data if isinstance(d.get('lat'), (int, float))]
    s = min(d['lat'] for d in pts) - .04; n = max(d['lat'] for d in pts) + .04
    w = min(d['lon'] for d in pts) - .04; e = max(d['lon'] for d in pts) + .04
    q = ('[out:csv(::lat,::lon,name,amenity,cuisine,opening_hours,"disused:amenity","was:amenity","addr:street","addr:housenumber",website,"contact:website";true;"\\t")]'
         f'[timeout:180][bbox:{s:.3f},{w:.3f},{n:.3f},{e:.3f}];'
         '(nwr["name"]["amenity"~"^(restaurant|bar|pub|cafe|fast_food|nightclub|hookah_lounge|ice_cream|biergarten|food_court|karaoke_box)$"];'
         'nwr["name"]["tourism"~"^(hotel|attraction)$"];nwr["name"]["leisure"~"^(escape_game|bowling_alley|amusement_arcade)$"];'
         'nwr["name"]["disused:amenity"];nwr["name"]["was:amenity"];);out center;')
    if csv_text is None:
        last = None
        for attempt in range(3):
            for ep in OVERPASS:
                try:
                    csv_text = http(ep, data=urllib.parse.urlencode({'data': q}).encode()); break
                except Exception as ex:
                    last = ex; print('Overpass', ep, 'falló:', ex)
            if csv_text: break
            time.sleep(30)
        if not csv_text: raise SystemExit(f'No se pudo descargar Overpass: {last}')
    rows = csv_text.split('\n'); head = rows.pop(0).split('\t')
    col = {k: i for i, k in enumerate(head)}
    pois = []
    for l in rows:
        c = l.split('\t')
        if len(c) < len(head) or not c[col['name']]: continue
        try: lat, lon = float(c[col['@lat']]), float(c[col['@lon']])
        except ValueError: continue
        g = lambda k: c[col[k]] if k in col else ''
        pois.append({'lat': lat, 'lon': lon, 'name': g('name'), 'amenity': g('amenity'), 'cuisine': g('cuisine'), 'oh': g('opening_hours'),
                     'closed': bool(g('disused:amenity') or g('was:amenity')),
                     'web': g('website') or g('contact:website'),
                     'addr': (g('addr:street') + (' ' + g('addr:housenumber') if g('addr:housenumber') else '')).strip()})
    return pois

import os, concurrent.futures, html as htmlmod
GKEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
import sys

def google_pass(data):
    """Google Places (solo tarifa básica «Pro», con tope mensual): ubica los que faltan y detecta cierres.
    Cada sitio se revisa como mucho una vez cada 30 días."""
    sys.path.insert(0, str(ROOT / 'tools'))
    from google_util import places, disponible
    today = datetime.date.today(); removed = []; calls = 0
    def due(d):
        g = d.get('gcheck')
        return not g or (today - datetime.date.fromisoformat(g)).days >= 30
    for d in data:
        if not due(d): continue
        if not disponible('pro'): print('Tope mensual de Google alcanzado.'); break
        zlat, zlon = d.get('zlat'), d.get('zlon')
        res = places('searchText', {'textQuery': f"{d['n']} {d.get('z') or ''} Madrid", 'maxResultCount': 3, 'languageCode': 'es',
                     'locationBias': {'circle': {'center': {'latitude': zlat or 40.4168, 'longitude': zlon or -3.7038}, 'radius': 8000.0 if zlat else 50000.0}}},
                     'places.id,places.displayName,places.businessStatus,places.location,places.formattedAddress')
        calls += 1
        best = None
        for pl in res:
            s = sim(d['n'], (pl.get('displayName') or {}).get('text', ''))
            loc = pl.get('location') or {}
            if s < .7 or 'latitude' not in loc: continue
            if km(40.4168, -3.7038, loc['latitude'], loc['longitude']) > 60: continue   # fuera de la Comunidad de Madrid
            dk = km(zlat, zlon, loc['latitude'], loc['longitude']) if zlat is not None else None
            if dk is not None and dk > 8: continue
            if not best or s > best[0]: best = (s, pl)
        d['gcheck'] = today.isoformat()
        if not best: continue
        pl = best[1]; st = pl.get('businessStatus')
        gname = (pl.get('displayName') or {}).get('text', '')
        if st == 'CLOSED_PERMANENTLY':
            if best[0] >= .88:   # solo se borra si el nombre coincide casi exactamente
                d['_remove'] = True; removed.append(f"{d['n']} ({d.get('z') or 'sin zona'}) = Google: «{gname}»"); print('CERRADO', d['n'], '=', gname, round(best[0], 2)); continue
            d['e'] = 'Revisar (posible cierre)'; print('DUDOSO', d['n'], '~', gname, round(best[0], 2)); continue
        if st == 'CLOSED_TEMPORARILY': d['e'] = 'Cerrado temporalmente'
        elif d.get('e') in ('Revisar (posible cierre)', 'Sin confirmar'): d['e'] = 'Abierto'
        if not d.get('locationVerified'):
            loc = pl['location']; d['lat'], d['lon'] = round(loc['latitude'], 6), round(loc['longitude'], 6)
            d['locationVerified'] = True; d['locSrc'] = 'google'
            if pl.get('formattedAddress'): d['addr'] = pl['formattedAddress'].split(', Madrid')[0]
    print('Consultas a Google (tarifa básica):', calls, '· cerrados definitivos:', len(removed))
    if removed:
        old = json.loads((ROOT / 'tools' / 'eliminados.json').read_text(encoding='utf-8')) if (ROOT / 'tools' / 'eliminados.json').exists() else []
        old += [{'fecha': today.isoformat(), **{k: v for k, v in d.items() if not k.startswith('_')}} for d in data if d.get('_remove')]
        (ROOT / 'tools' / 'eliminados.json').write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')
    return removed

OG = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image)["\'][^>]*>', re.I)
def og_image(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RENTA-preview/1.0)', 'Accept': 'text/html'})
        with urllib.request.urlopen(req, timeout=10) as r:
            if 'html' not in (r.headers.get('Content-Type') or ''): return None
            page = r.read(400000).decode('utf-8', 'ignore')
        for tag in OG.findall(page):
            m = re.search(r'content=["\']([^"\']+)', tag, re.I)
            if not m: continue
            img = urllib.parse.urljoin(url, htmlmod.unescape(m.group(1).strip()))
            if img.startswith('https://') and not re.search(r'logo|favicon|icon|placeholder|default', img, re.I): return img
    except Exception:
        return None
    return None

def photos_pass(data):
    """Foto oficial: la imagen de vista previa (og:image) de la web del propio local."""
    todo = [d for d in data if d.get('web') and not d.get('photo') and not d.get('_remove') and not d.get('photoTried')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for d, img in zip(todo, ex.map(lambda d: og_image(d['web'] if d['web'].startswith('http') else 'https://' + d['web']), todo)):
            if img: d['photo'] = img
            else: d['photoTried'] = datetime.date.today().isoformat()
    print('Fotos encontradas:', sum(1 for d in todo if d.get('photo')), 'de', len(todo), 'webs')

def main():
    offline_csv = open(sys.argv[1], encoding='utf-8').read() if len(sys.argv) > 1 else None
    use_nominatim = '--sin-nominatim' not in sys.argv
    lines, i, data = load_data()
    pois = overpass_pois(data, offline_csv)
    print(len(pois), 'locales del mapa abierto')
    index = {}
    for k, p in enumerate(pois):
        for t in set(tokens(p['name'])):
            if len(t) >= 3: index.setdefault(t, []).append(k)
    shared = {}
    for d in data:
        if isinstance(d.get('lat'), (int, float)):
            key = f"{d['lat']:.3f},{d['lon']:.3f}"; shared[key] = shared.get(key, 0) + 1
    found = closed = nomi = 0; missing = []
    for d in data:
        if d.get('verifiedAt') or d.get('locSrc') == 'google': continue   # lo ubicado por Google se conserva
        # Cada ejecución empieza de cero desde el centro de barrio original
        if d.get('zlat') is not None:
            d['lat'], d['lon'] = d['zlat'], d['zlon']
            for k in ('locationVerified', 'oh', 'osmCuisine', 'addr', 'locSrc'): d.pop(k, None)
        has = isinstance(d.get('zlat', d.get('lat')), (int, float))
        zlat, zlon = d.get('zlat', d.get('lat')), d.get('zlon', d.get('lon'))
        radius = (4.5 if shared.get(f'{zlat:.3f},{zlon:.3f}', 0) > 3 else 2.5) if has else None
        best = None
        for k in {k for t in tokens(d['n']) for k in index.get(t, [])}:
            p = pois[k]; s = sim(d['n'], p['name'])
            if s < .8: continue
            dk = km(zlat, zlon, p['lat'], p['lon']) if has else None
            if dk is not None and dk > radius: continue
            if dk is None and s < .95: continue
            # Cadenas: "Massart Pizza - Goya" solo vale si el local del mapa está en Goya
            br = branch(d['n'])
            if br and not branch(p['name']):
                words = [w for w in br.split() if len(w) >= 4]
                where = strip(p['name'] + ' ' + p['addr'])
                if words and any(w in where for w in words): s = min(1, s + .05)
                elif words: continue
            score = s - (dk or 0) / 10
            if not best or score > best[0]: best = (score, p)
        if has and 'zlat' not in d: d['zlat'], d['zlon'] = zlat, zlon   # guarda el centro de barrio original
        if best:
            p = best[1]
            d['lat'], d['lon'] = round(p['lat'], 6), round(p['lon'], 6); d['locationVerified'] = True
            if p['oh']: d['oh'] = p['oh']
            if p['cuisine']: d['osmCuisine'] = p['cuisine']
            if p['addr']: d['addr'] = p['addr']
            if p.get('web') and not d.get('web'): d['web'] = p['web']
            d['locSrc'] = 'osm'
            if p['closed']: d['e'] = 'Revisar (posible cierre)'; closed += 1
            found += 1
        else:
            missing.append(d)
    print('Emparejados con Overpass:', found)
    if use_nominatim:
        for d in missing:
            q = f"{d['n']}, {d.get('z') or ''} Madrid".replace(' ,', ',')
            try:
                res = json.loads(http('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
                    {'q': q, 'format': 'jsonv2', 'limit': 3, 'countrycodes': 'es', 'extratags': 1, 'addressdetails': 1, 'accept-language': 'es'}), timeout=30))
            except Exception as ex:
                print('Nominatim falló para', d['n'], ex); time.sleep(2); continue
            time.sleep(1.1)
            for r in res:
                if r.get('category') not in ('amenity', 'tourism', 'leisure', 'shop'): continue
                s = sim(d['n'], r.get('name') or r.get('display_name', '').split(',')[0])
                lat, lon = float(r['lat']), float(r['lon'])
                zlat, zlon = d.get('zlat'), d.get('zlon')
                if s < .75 or (zlat is not None and km(zlat, zlon, lat, lon) > 8) or km(40.4168, -3.7038, lat, lon) > 60: continue
                ex = r.get('extratags') or {}; a = r.get('address') or {}
                d['lat'], d['lon'] = round(lat, 6), round(lon, 6); d['locationVerified'] = True
                if ex.get('opening_hours'): d['oh'] = ex['opening_hours']
                if ex.get('cuisine'): d['osmCuisine'] = ex['cuisine']
                if a.get('road'): d['addr'] = a['road'] + (' ' + a['house_number'] if a.get('house_number') else '')
                nomi += 1; break
    removed = google_pass(data) if GKEY else []
    photos_pass(data)
    data = [d for d in data if not d.get('_remove')]
    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')
    total = len(data); ok = sum(1 for d in data if d.get('locationVerified'))
    resumen = [f'Ubicación del {datetime.date.today().isoformat()}',
               f'{ok} de {total} sitios con coordenadas reales ({found} por mapa abierto, {nomi} por búsqueda individual).',
               f'{closed} marcados como posible cierre en el mapa.',
               f'{len(removed)} eliminados por estar cerrados definitivamente según Google.',
               f'{sum(1 for d in data if d.get("photo"))} con foto de su web oficial.', '',
               'Eliminados:'] + ['- ' + r for r in removed] + ['', 'Sin ubicar:'] + \
              ['- ' + d['n'] + (' (' + d['z'] + ')' if d.get('z') else '') for d in data if not d.get('locationVerified')]
    (ROOT / 'tools' / 'ultima_ubicacion.txt').write_text('\n'.join(resumen) + '\n', encoding='utf-8')
    print('\n'.join(resumen[:3]))

if __name__ == '__main__':
    main()
