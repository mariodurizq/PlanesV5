"""Genera páginas estáticas para Google: «Las mejores coctelerías en Chamberí», «Los mejores mexicanos en Madrid»…

Se ejecuta en cada publicación (publicar.yml) sobre la carpeta _site, a partir de la lista de sitios de
index.html (y de nuevos.json si existe). No usa ninguna API: solo lee los datos que ya tiene la web.
Crea _site/mejores/*.html, _site/mejores/index.html, _site/sitemap.xml y _site/robots.txt.
"""
import html, json, math, pathlib, re, sys, unicodedata, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '_site')
BASE = 'https://mariodurizq.github.io/PlanesV5/'
MARCA = 'RENTA'
HOY = datetime.date.today()
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
FECHA = f'{MESES[HOY.month - 1]} de {HOY.year}'

# categoría de la web -> (slug, título en plural, género 'f'/'m', icono, tipo schema.org)
CATS = {
    'Coctelería': ('coctelerias', 'coctelerías', 'f', '🍸', 'BarOrPub'),
    'Shisha Lounge': ('shishas', 'shishas', 'f', '💨', 'BarOrPub'),
    'Rooftop/Terraza': ('rooftops-terrazas', 'rooftops y terrazas', 'm', '🌇', 'BarOrPub'),
    'Bar/Cervecería': ('bares-cervecerias', 'bares y cervecerías', 'm', '🍺', 'BarOrPub'),
    'Discoteca/Club': ('discotecas', 'discotecas', 'f', '🪩', 'NightClub'),
    'Asiática': ('restaurantes-asiaticos', 'restaurantes asiáticos y japoneses', 'm', '🍣', 'Restaurant'),
    'Italiana/Pizza': ('italianos-pizzerias', 'italianos y pizzerías', 'm', '🍕', 'Restaurant'),
    'Española/Mediterránea': ('comida-espanola', 'restaurantes de comida española', 'm', '🥘', 'Restaurant'),
    'Hamburguesas': ('hamburguesas', 'hamburgueserías', 'f', '🍔', 'Restaurant'),
    'Mexicana': ('mexicanos', 'restaurantes mexicanos', 'm', '🌮', 'Restaurant'),
    'Carnes/Parrilla': ('asadores-carnes', 'asadores y carnes a la brasa', 'm', '🥩', 'Restaurant'),
    'Café/Brunch/Postres': ('brunch-cafeterias', 'sitios de brunch y cafeterías', 'm', '🥞', 'CafeOrCoffeeShop'),
}
COMIDA = {'Asiática', 'Italiana/Pizza', 'Española/Mediterránea', 'Hamburguesas', 'Mexicana', 'Carnes/Parrilla', 'Restaurante (general)'}
CATS_EXTRA = {'restaurantes': ('restaurantes', 'restaurantes', 'm', '🍽️', 'Restaurant')}


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def e(s):
    return html.escape(str(s or ''), quote=True)


def cargar():
    txt = (ROOT / 'index.html').read_text(encoding='utf-8')
    i = txt.index('[', txt.index('const DATA'))
    depth = 0
    for k in range(i, len(txt)):
        if txt[k] == '[': depth += 1
        elif txt[k] == ']':
            depth -= 1
            if depth == 0: break
    data = json.loads(txt[i:k + 1])
    nuevos = ROOT / 'nuevos.json'
    if nuevos.exists():
        try:
            for s in json.loads(nuevos.read_text(encoding='utf-8')).get('sitios', []):
                if not any(d['n'] == s.get('n') for d in data): data.append(s)
        except Exception as ex:
            print('nuevos.json no se pudo leer:', ex)
    vivos = [d for d in data if d.get('e') != 'Cerrado definitivamente' and not d.get('cerradoDesde')
             and d.get('v') and d.get('nr')]
    # zona: la que tenga o la del sitio con zona más cercano (≤1,2 km)
    con_z = [d for d in vivos if d.get('z') and d.get('lat')]
    for d in vivos:
        if d.get('z') or not d.get('lat'): continue
        mejor = min(con_z, key=lambda x: (x['lat'] - d['lat']) ** 2 + ((x['lon'] - d['lon']) * 0.77) ** 2, default=None)
        if mejor and math.hypot(mejor['lat'] - d['lat'], (mejor['lon'] - d['lon']) * 0.77) * 111 <= 1.2:
            d['z'] = mejor['z']
    return vivos


def puntuacion(d):
    return (d.get('v') or 0) + math.log10(max(d.get('nr') or 1, 1)) * 0.25


def pagina(path, titulo, h1, intro, sitios, otras, tipo):
    url = BASE + path
    items = []
    for i, d in enumerate(sitios, 1):
        maps = 'https://www.google.com/maps/search/?api=1&query=' + (
            f"{d['lat']},{d['lon']}" if d.get('lat') else e(d['n'] + ' ' + (d.get('addr') or 'Madrid')))
        precio = f" · {e(d['p'])} €" if d.get('p') else ''
        web = f' · <a href="{e(d["web"])}" rel="nofollow noopener" target="_blank">Web</a>' if d.get('web') else ''
        desc = e(d.get('info') or d.get('no') or '')
        items.append(f'''<li class="s"><div class="n"><span class="pos">{i}</span><div><h2>{e(d['n'])}</h2>
<p class="m">{e(d.get('cd') or d.get('cm'))} · {e(d.get('z') or 'Madrid')}{precio}</p>
<p class="r">★ {float(d['v']):.1f} <small>({int(d['nr'])} reseñas en Google)</small></p>
{f'<p class="d">{desc}</p>' if desc else ''}<p class="a">{e(d.get('addr') or '')}</p>
<p class="l"><a href="{maps}" target="_blank" rel="noopener">📍 Cómo llegar</a>{web} · <a href="../?sitio={e(d['n'])}">Ver en {MARCA}</a></p></div></div></li>''')
    ld = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': h1, 'url': url, 'numberOfItems': len(sitios),
          'itemListElement': [{'@type': 'ListItem', 'position': i, 'item': {
              '@type': tipo, 'name': d['n'], **({'address': d['addr']} if d.get('addr') else {}),
              **({'geo': {'@type': 'GeoCoordinates', 'latitude': d['lat'], 'longitude': d['lon']}} if d.get('lat') else {}),
              **({'priceRange': d['p'] + ' €'} if d.get('p') else {})}} for i, d in enumerate(sitios, 1)]}
    rel = ''.join(f'<a href="{e(h)}">{e(t)}</a>' for h, t in otras)
    desc_meta = intro[:155]
    return f'''<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titulo)}</title><meta name="description" content="{e(desc_meta)}">
<link rel="canonical" href="{e(url)}"><meta property="og:title" content="{e(titulo)}"><meta property="og:description" content="{e(desc_meta)}">
<meta property="og:type" content="article"><meta property="og:url" content="{e(url)}"><meta name="theme-color" content="#0A0F1C">
<link rel="icon" href="../icon-192.png"><link rel="apple-touch-icon" href="../apple-touch-icon.png">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;background:#0b100e;color:#f1efe8;line-height:1.5}}
main{{max-width:760px;margin:0 auto;padding:20px 16px 60px}}a{{color:#c5e3a0}}header a.brand{{font-weight:900;font-size:22px;text-decoration:none;color:#f1efe8;letter-spacing:-.5px}}
h1{{font-size:28px;line-height:1.15;margin:18px 0 8px}}.intro{{color:#b9c0b8}}.cta{{display:inline-block;margin:12px 0 18px;padding:12px 16px;border-radius:12px;background:#c5e3a0;color:#0b1210;font-weight:800;text-decoration:none}}
ol{{list-style:none;padding:0;margin:0}}.s{{border:1px solid #24302b;border-radius:16px;padding:14px;margin:10px 0;background:#121a17}}.n{{display:flex;gap:12px}}
.pos{{flex:0 0 32px;height:32px;border-radius:50%;background:#1f2b26;display:grid;place-items:center;font-weight:800}}h2{{font-size:18px;margin:2px 0}}
.m,.a{{color:#9aa59e;font-size:13.5px;margin:2px 0}}.r{{margin:4px 0;font-weight:700}}.r small{{font-weight:400;color:#9aa59e}}.d{{font-size:14px;margin:6px 0}}.l{{font-size:14px;margin:8px 0 0}}
nav.rel{{margin-top:30px}}nav.rel h3{{font-size:16px}}nav.rel a{{display:inline-block;margin:4px 6px 4px 0;padding:7px 11px;border:1px solid #24302b;border-radius:999px;text-decoration:none;font-size:13.5px}}
footer{{margin-top:30px;font-size:12.5px;color:#7f8a83}}</style></head><body><main>
<header><a class="brand" href="../">{MARCA}</a> <span style="color:#7f8a83">· Planes en Madrid</span></header>
<h1>{e(h1)}</h1><p class="intro">{e(intro)}</p>
<a class="cta" href="../">✨ Monta tu plan con {MARCA}</a>
<ol>{''.join(items)}</ol>
<nav class="rel"><h3>Más listas</h3>{rel}</nav>
<footer>Actualizado en {FECHA}. Valoraciones y número de reseñas según Google Maps; horarios y precios pueden cambiar, compruébalos antes de ir.
¿Algún dato mal? Avísanos desde la ficha del sitio en {MARCA}. · <a href="../legal.html">Aviso legal y privacidad</a></footer></main></body></html>'''


def main():
    sitios = cargar()
    out = SITE / 'mejores'; out.mkdir(parents=True, exist_ok=True)
    zonas = {}
    for d in sitios:
        if d.get('z'): zonas.setdefault(d['z'], []).append(d)
    paginas = []   # (archivo, título corto, zona, cat)

    def grupo(cat):
        if cat == 'restaurantes': return [d for d in sitios if d.get('cm') in COMIDA]
        return [d for d in sitios if d.get('cm') == cat]

    todas = list(CATS.items()) + list(CATS_EXTRA.items())
    plan = []
    for cat, (sl, plural, gen, ico, tipo) in todas:
        lista = sorted(grupo(cat), key=puntuacion, reverse=True)
        art = 'Las mejores' if gen == 'f' else 'Los mejores'
        if len(lista) >= 4:
            plan.append((f'{sl}-madrid.html', f'{art} {plural} de Madrid', 'Madrid', cat, lista[:25], tipo, ico))
        for z, zs in zonas.items():
            lz = sorted([d for d in zs if d in lista], key=puntuacion, reverse=True)
            if len(lz) >= 3:
                plan.append((f'{sl}-{slug(z)}.html', f'{art} {plural} en {z}', z, cat, lz[:20], tipo, ico))

    por_zona, por_cat = {}, {}
    for p in plan:
        por_zona.setdefault(p[2], []).append(p); por_cat.setdefault(p[3], []).append(p)

    for fn, h1, z, cat, lista, tipo, ico in plan:
        media = sum(d['v'] for d in lista) / len(lista)
        reseñas = sum(int(d['nr']) for d in lista)
        intro = (f'{len(lista)} sitios elegidos por su valoración en Google (media {media:.1f} ★ con {reseñas:,} reseñas en total)'
                 f'{"" if z == "Madrid" else " en la zona de " + z}. Lista revisada en {FECHA}.').replace(',', '.')
        otras = [(q[0], q[1]) for q in por_zona.get(z, []) if q[0] != fn][:10]
        otras += [(q[0], q[1]) for q in por_cat.get(cat, []) if q[0] != fn and q[2] != z][:12]
        titulo = f'{h1} ({MESES[HOY.month - 1]} {HOY.year}) | {MARCA}'
        (out / fn).write_text(pagina('mejores/' + fn, titulo, h1, intro, lista, otras, tipo), encoding='utf-8')
        paginas.append(fn)

    # índice
    bloques = []
    for z in ['Madrid'] + sorted(k for k in por_zona if k != 'Madrid'):
        if z not in por_zona: continue
        enl = ''.join(f'<li><a href="{e(p[0])}">{p[6]} {e(p[1])}</a></li>' for p in sorted(por_zona[z], key=lambda p: p[1]))
        bloques.append(f'<h2>{e("Toda Madrid" if z == "Madrid" else z)}</h2><ul>{enl}</ul>')
    idx = f'''<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Los mejores sitios de Madrid por zona y tipo | {MARCA}</title>
<meta name="description" content="Listas de las mejores coctelerías, shishas, restaurantes, rooftops y discotecas de Madrid por barrio, según valoraciones en Google. Actualizado en {FECHA}.">
<link rel="canonical" href="{BASE}mejores/"><link rel="icon" href="../icon-192.png">
<style>body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;background:#0b100e;color:#f1efe8;line-height:1.55}}main{{max-width:760px;margin:0 auto;padding:20px 16px 60px}}
a{{color:#c5e3a0}}h1{{font-size:28px}}h2{{font-size:19px;margin-top:26px}}ul{{padding-left:18px}}</style></head><body><main>
<a href="../" style="font-weight:900;font-size:22px;color:#f1efe8;text-decoration:none">{MARCA}</a>
<h1>Los mejores sitios de Madrid</h1><p>Listas por zona y tipo, ordenadas por valoración en Google. Actualizado en {FECHA}.</p>
{''.join(bloques)}</main></body></html>'''
    (out / 'index.html').write_text(idx, encoding='utf-8')

    urls = [BASE, BASE + 'mejores/'] + [BASE + 'mejores/' + p for p in paginas]
    (SITE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + ''.join(f'<url><loc>{e(u)}</loc><lastmod>{HOY.isoformat()}</lastmod></url>\n' for u in urls)
                                      + '</urlset>\n', encoding='utf-8')
    (SITE / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n', encoding='utf-8')
    print(f'{len(paginas)} páginas + índice + sitemap ({len(sitios)} sitios)')


if __name__ == '__main__':
    main()
