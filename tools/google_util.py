"""Llamadas a Google Places (API nueva) desde GitHub Actions, con TOPE MENSUAL para no pagar nunca.

Google da gratis cada mes (por SKU): Pro 5.000 consultas, Enterprise 1.000.
Aquí nos quedamos muy por debajo: Pro 3.000 y Enterprise 500 al mes, contados en tools/google_uso.json.
Si se llega al tope, las llamadas se cortan y el proceso sigue sin Google.
"""
import json, os, time, datetime, pathlib, urllib.request, urllib.error

KEY = os.environ.get('GOOGLE_PLACES_KEY', '').strip()
USO = pathlib.Path(__file__).resolve().parent / 'google_uso.json'
TOPE = {'pro': 3000, 'enterprise': 500}
ENTERPRISE_FIELDS = ('rating', 'userRatingCount', 'websiteUri', 'priceLevel', 'regularOpeningHours', 'currentOpeningHours', 'nationalPhoneNumber', 'reviews')
CALLS = {'n': 0}

def _mes():
    return datetime.date.today().strftime('%Y-%m')

def _leer():
    try: return json.loads(USO.read_text(encoding='utf-8'))
    except Exception: return {}

def _guardar(u):
    USO.write_text(json.dumps(u, indent=1, ensure_ascii=False), encoding='utf-8')

def sku(fields):
    return 'enterprise' if any(f in fields for f in ENTERPRISE_FIELDS) else 'pro'

def disponible(s, n=1):
    u = _leer().get(_mes(), {})
    return KEY and u.get(s, 0) + n <= TOPE[s]

def places(endpoint, body, fields):
    """endpoint: 'searchText' o 'searchNearby'. Devuelve la lista de lugares, o [] si no hay clave o se llegó al tope."""
    s = sku(fields)
    if not disponible(s):
        if not getattr(places, '_avisado', False):
            print(f'Tope mensual gratuito de Google ({s}) alcanzado: se omite Google hasta el mes que viene.'); places._avisado = True
        return []
    req = urllib.request.Request(f'https://places.googleapis.com/v1/places:{endpoint}', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'X-Goog-Api-Key': KEY, 'X-Goog-FieldMask': fields})
    for intento in range(2):
        u = _leer(); m = u.setdefault(_mes(), {}); m[s] = m.get(s, 0) + 1; _guardar(u)   # se cuenta antes de llamar
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                CALLS['n'] += 1; time.sleep(0.15)
                return json.loads(r.read().decode()).get('places', [])
        except urllib.error.HTTPError as ex:
            print('Google', ex.code, ex.read().decode()[:300])
            if ex.code in (400, 401, 403, 429): return []
            time.sleep(3)
        except Exception as ex:
            print('Google falló:', ex); time.sleep(3)
    return []
