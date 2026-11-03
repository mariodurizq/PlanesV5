"""Descarga la agenda de actividades del Ayuntamiento de Madrid (datos abiertos) y genera eventos.json.

Se ejecuta a diario en GitHub Actions (.github/workflows/eventos.yml).
Fuente: datos.madrid.es — «Actividades culturales y de ocio municipal en los próximos 100 días».
"""
import json, re, sys, datetime, urllib.request, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = 'https://datos.madrid.es/egob/catalogo/206974-0-agenda-eventos-culturales-100.json'
UA = 'RENTA-planes-madrid/1.0 (github.com/mariodurizq/PlanesV5)'
GASTRO = re.compile(r'gastron|mercado|feria|tapa|vino|cerveza|comida|cocina|degustaci|food|chocolate|churro|aliment', re.I)

def clean(t):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', str(t or '')))
    return re.sub(r'\s+', ' ', t).strip()

def date(s):
    m = re.match(r'(\d{4}-\d{2}-\d{2})', str(s or ''))
    return m.group(1) if m else None

def kind(e):
    t = (str(e.get('@type', '')) + ' ' + str(e.get('title', '')) + ' ' + str(e.get('description', ''))).lower()
    for k, rx in [('Gastronomía', GASTRO), ('Música', re.compile(r'concierto|musica|música|jazz|flamenco|orquesta|coro', re.I)),
                  ('Teatro y danza', re.compile(r'teatro|danza|ballet|circo|mon[oó]logo', re.I)), ('Cine', re.compile(r'cine|proyecci|film', re.I)),
                  ('Exposiciones', re.compile(r'exposici|muestra|galer', re.I)), ('Infantil', re.compile(r'infantil|niñ|familia', re.I)),
                  ('Deporte', re.compile(r'deport|carrera|yoga|marcha|ruta', re.I)), ('Talleres', re.compile(r'taller|curso', re.I))]:
        if rx.search(t): return k
    return 'Otros'

def main():
    raw = open(sys.argv[1], encoding='utf-8').read() if len(sys.argv) > 1 else \
        urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': UA, 'Accept': 'application/json'}), timeout=90).read().decode('utf-8', 'ignore')
    data = json.loads(raw)
    items = data.get('@graph', data if isinstance(data, list) else [])
    today = datetime.date.today(); limit = today + datetime.timedelta(days=60)
    out = []
    for e in items:
        start, end = date(e.get('dtstart')), date(e.get('dtend')) or date(e.get('dtstart'))
        if not start or not end: continue
        if datetime.date.fromisoformat(end) < today or datetime.date.fromisoformat(start) > limit: continue
        loc = e.get('location') or {}; addr = (e.get('address') or {}).get('area') or {}
        title = clean(e.get('title'))
        if not title: continue
        out.append({
            'n': title[:140], 'start': start, 'end': end, 'time': clean(e.get('time'))[:20],
            'place': clean(e.get('event-location'))[:120], 'addr': clean(addr.get('street-address'))[:120],
            'lat': loc.get('latitude'), 'lon': loc.get('longitude'),
            'url': e.get('link') or '', 'free': str(e.get('free')) in ('1', 'True', 'true'), 'price': clean(e.get('price'))[:80],
            'cat': kind(e), 'desc': clean(e.get('description'))[:280],
        })
    out.sort(key=lambda x: (x['start'], x['n']))
    seen, uniq = set(), []
    for x in out:
        k = (x['n'], x['start'], x['place'])
        if k not in seen: seen.add(k); uniq.append(x)
    (ROOT / 'eventos.json').write_text(json.dumps({'actualizado': today.isoformat(), 'fuente': 'Ayuntamiento de Madrid · datos.madrid.es', 'eventos': uniq}, ensure_ascii=False), encoding='utf-8')
    print(len(uniq), 'eventos guardados')

if __name__ == '__main__':
    main()
