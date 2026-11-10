// Pruebas que deben pasar antes de publicar la web (se ejecutan en GitHub Actions)
const { chromium, devices } = require('playwright');
const fs = require('fs');
const BASE = process.argv[2] || 'http://127.0.0.1:8080/';
const fallos = []; const ok = (cond, msg) => { console.log((cond ? '✔ ' : '✘ ') + msg); if (!cond) fallos.push(msg); };
(async () => {
  for (const f of ['comer-offline.json', 'eventos.json', 'mercados.json', 'nuevos.json', 'tiempo.json', 'manifest.webmanifest']) {
    if (!fs.existsSync(f)) continue;
    try { JSON.parse(fs.readFileSync(f, 'utf8')); ok(true, `${f} es válido`); } catch (e) { ok(false, `${f} está roto: ${e.message}`); }
  }
  { const sw = (fs.readFileSync('service-worker.js', 'utf8').match(/VERSION = '([^']+)'/) || [])[1];
    const pg = (fs.readFileSync('index.html', 'utf8').match(/RENTA_VERSION='([^']+)'/) || [])[1];
    ok(sw && sw === pg, `la versión de la página (${pg}) coincide con la del service worker (${sw})`); }
  const b = await chromium.launch();
  for (const [nombre, opts] of [['móvil', { ...devices['iPhone 13'] }], ['escritorio', { viewport: { width: 1366, height: 860 } }]]) {
    const c = await b.newContext({ ...opts, locale: 'es-ES' });
    // El mapa abierto y Nominatim no se llaman en las pruebas
    await c.route(/overpass|nominatim|places\.googleapis/, r => r.fulfill({ status: 504, body: '' }));
    const p = await c.newPage(); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(BASE, { waitUntil: 'load' }); await p.waitForTimeout(2500);
    const info = await p.evaluate(() => ({
      datos: typeof DATA !== 'undefined' ? DATA.length : 0,
      tabs: [...document.querySelectorAll('#tabbar button')].filter(x => x.offsetParent).length,
      pines: document.querySelectorAll('#radarMap .leaflet-marker-icon').length,
      resultados: document.getElementById('resultsCount')?.textContent || ''
    }));
    ok(info.datos > 300, `[${nombre}] catálogo cargado (${info.datos} sitios)`);
    ok(info.tabs === 4, `[${nombre}] 4 pestañas visibles`);
    ok(info.pines > 10, `[${nombre}] el mapa pinta sitios (${info.pines} marcadores o grupos)`);
    ok(/\d+ resultados/.test(info.resultados), `[${nombre}] Explorar muestra resultados (${info.resultados})`);
    await p.click('#tabPide'); await p.fill('#pideText', 'cena japonesa en Chamberí'); await p.click('#pideBtn');
    for (let i = 0; i < 40; i++) { await p.waitForTimeout(250); if (!(await p.evaluate(() => !!document.querySelector('#pideResults .thinking')))) break; }
    const pide = await p.evaluate(() => ({ lugar: pdLast?.place?.n, n: (pdRun._items || []).length }));
    ok(pide.lugar === 'Chamberí' && pide.n > 0, `[${nombre}] Pídeme entiende la zona (${pide.lugar}, ${pide.n} resultados)`);
    for (const t of ['tabEventos', 'tabMatch', 'tabGuiado']) { await p.click('#' + t); await p.waitForTimeout(400); }
    ok(errs.length === 0, `[${nombre}] sin errores de JavaScript ${errs.slice(0, 3).join(' | ')}`);
    await c.close();
  }
  await b.close();
  if (fallos.length) { console.log(`\n${fallos.length} prueba(s) fallida(s): NO se publica.`); process.exit(1); }
  console.log('\nTodo correcto: se publica.');
})();
