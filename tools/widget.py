"""Genera widget.json: lo que lee el widget del iPhone (Scriptable).

Una selección de sitios con sus sellos (sin notas de Google), el tiempo de los próximos días y los
eventos cercanos. Se crea en cada publicación (publicar.yml) dentro de _site; no usa ninguna API.
"""
import json, math, re, sys, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '_site')
sys.path.insert(0, str(ROOT / 'tools'))
from paginas import cargar, puntuacion, calcular_sellos, _SELLOS  # noqa: E402

# franja → categorías que encajan
TIPO = {
    'Café/Brunch/Postres': 'cafe', 'Coctelería': 'copas', 'Rooftop/Terraza': 'terraza', 'Bar/Cervecería': 'canas',
    'Shisha Lounge': 'shisha', 'Discoteca/Club': 'fiesta',
}
AFUERA = re.compile(r'terraza|rooftop|azotea|jard[ií]n|aire libre|chiringuito|mirador', re.I)


def main():
    sitios = cargar()
    calcular_sellos(sitios)
    out = []
    for d in sitios:
        if not isinstance(d.get('lat'), (int, float)): continue
        sellos = _SELLOS.get(d['n'], [])
        tipo = TIPO.get(d.get('cm'), 'comer')
        out.append({'n': d['n'], 'c': d.get('cd') or d.get('cm') or '', 't': tipo, 'z': d.get('z') or '',
                    'la': round(d['lat'], 5), 'lo': round(d['lon'], 5), 'p': d.get('p') or '',
                    's': sellos[:2], 'f': 1 if AFUERA.search(' '.join([d.get('cm') or '', d.get('cd') or '', d['n']])) else 0,
                    'k': round(puntuacion(d), 3)})
    # se quedan los mejores de cada tipo (el widget elige según la hora, el tiempo y dónde estés)
    por_tipo = {}
    for x in sorted(out, key=lambda x: -x['k']): por_tipo.setdefault(x['t'], []).append(x)
    sel = [x for v in por_tipo.values() for x in v[:120]]
    for x in sel: x.pop('k', None)

    tiempo = {}
    try: tiempo = json.loads((ROOT / 'tiempo.json').read_text(encoding='utf-8'))
    except Exception: pass
    eventos = []
    try:
        hoy = datetime.date.today(); fin = hoy + datetime.timedelta(days=3)
        for e in json.loads((ROOT / 'eventos.json').read_text(encoding='utf-8')).get('eventos', []):
            ini, fn = datetime.date.fromisoformat(e['start']), datetime.date.fromisoformat(e['end'])
            if fn < hoy or ini > fin or (fn - ini).days > 10 or not e.get('lat'): continue
            eventos.append({'n': e['n'], 'd': e['start'], 'f': e['end'], 'h': e.get('time') or '', 'l': e.get('place') or '',
                            'c': e.get('cat') or '', 'g': 1 if e.get('free') else 0, 'la': float(e['lat']), 'lo': float(e['lon']), 'u': e.get('url') or ''})
        eventos = sorted(eventos, key=lambda e: (e['d'], e['h'] or '99'))[:60]
    except Exception as ex:
        print('eventos:', ex)
    data = {'v': 1, 'generado': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M'),
            'tiempo': (tiempo.get('dias') or [])[:4], 'sitios': sel, 'eventos': eventos}
    (SITE / 'widget.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'widget.json: {len(sel)} sitios, {len(eventos)} eventos')


if __name__ == '__main__':
    main()
