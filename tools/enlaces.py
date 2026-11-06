"""Cada semana: revisa las webs y fotos de tus sitios.

- Foto que ya no carga → se quita (la app vuelve a la foto genérica).
- Web que no responde dos semanas seguidas → se marca «webCaida» (aviso en la ficha; puede indicar un cierre).
- Sitios con web y sin foto → se intenta sacar la foto oficial de la web (cada 30 días como mucho).
Sin Google, sin coste. Resumen en tools/ultima_revision_enlaces.txt.
"""
import json, sys, datetime, pathlib, urllib.request, urllib.error, concurrent.futures
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from ubicar import load_data, og_image

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'Mozilla/5.0 (compatible; RENTA-revision/1.0)', 'Accept': '*/*'}

def responde(url, imagen=False):
    for metodo in ('HEAD', 'GET'):
        try:
            req = urllib.request.Request(url, headers=UA, method=metodo)
            with urllib.request.urlopen(req, timeout=12) as r:
                if r.status >= 400: continue
                if imagen and not (r.headers.get('Content-Type') or '').startswith('image'): return False
                return True
        except urllib.error.HTTPError as ex:
            if ex.code in (403, 405, 429) and metodo == 'HEAD': continue   # muchas webs rechazan HEAD o bots
            if ex.code in (403, 429): return True                          # existe, aunque bloquee al robot
        except Exception:
            pass
    return False

def main():
    lines, i, data = load_data()
    hoy = datetime.date.today(); h = hoy.isoformat()
    url = lambda w: w if w.startswith('http') else 'https://' + w
    fotos = [d for d in data if d.get('photo')]
    webs = [d for d in data if d.get('web')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        ok_fotos = list(ex.map(lambda d: responde(d['photo'], True), fotos))
        ok_webs = list(ex.map(lambda d: responde(url(d['web'])), webs))
    quitadas = caidas = recuperadas = 0
    for d, ok in zip(fotos, ok_fotos):
        if not ok: d.pop('photo', None); d['photoTried'] = h; quitadas += 1
    for d, ok in zip(webs, ok_webs):
        if ok:
            a = d.pop('webCaida', None); d.pop('webFallo', None)
            if a: recuperadas += 1
        elif d.get('webFallo'):
            if not d.get('webCaida'): caidas += 1
            d['webCaida'] = d.get('webCaida') or h
        else:
            d['webFallo'] = h
    # Fotos nuevas desde la web oficial
    def toca(d):
        t = d.get('photoTried')
        return d.get('web') and not d.get('photo') and not d.get('webCaida') and (not t or (hoy - datetime.date.fromisoformat(t)).days >= 30)
    cands = [d for d in data if toca(d)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda d: og_image(url(d['web'])), cands))
    nuevas = 0
    for d, img in zip(cands, res):
        if img: d['photo'] = img; d.pop('photoTried', None); nuevas += 1
        else: d['photoTried'] = h
    lines[i] = 'const DATA = ' + json.dumps(data, ensure_ascii=False) + ';'
    (ROOT / 'index.html').write_text('\n'.join(lines), encoding='utf-8')
    resumen = (f'Revisión del {h}: {len(fotos)} fotos ({quitadas} rotas quitadas, {nuevas} nuevas) · '
               f'{len(webs)} webs ({caidas} caídas nuevas, {recuperadas} recuperadas) · '
               f'{sum(1 for d in data if d.get("webCaida"))} webs caídas en total')
    caidas_l = [f"- {d['n']}: {d['web']} (sin responder desde {d['webCaida']})" for d in data if d.get('webCaida')]
    (ROOT / 'tools' / 'ultima_revision_enlaces.txt').write_text(resumen + '\n\nWebs caídas (posible cierre):\n' + '\n'.join(caidas_l) + '\n', encoding='utf-8')
    print(resumen)

if __name__ == '__main__':
    main()
