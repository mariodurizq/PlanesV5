// Me Renta · widget para iPhone (app Scriptable)
// Sugiere un sitio según la hora, el tiempo y dónde estés, y te dice el tiempo y un evento de hoy.
// Lee https://mariodurizq.github.io/PlanesV5/widget.json (se actualiza solo cada día). Sin claves ni cuentas.
// Tamaños: pequeño (1 sugerencia), mediano (sugerencia + tiempo + evento) y grande (3 sugerencias + eventos).

const BASE = 'https://mariodurizq.github.io/PlanesV5/';
const C = { bg1: '#0b0b0b', bg2: '#2a0a10', ink: '#f5f5f5', mut: '#a9a3a3', acc: '#e3263c', lime: '#f6c7cd', or: '#e8a24a' };
const SELLO = { top: '🏆 Imprescindible', zona: '📍 Top de la zona', joya: '💎 Joya escondida', michelin: '🎖️ Guía Michelin', nuevo: '✨ Nuevo' };
const ICON = { cafe: '☕', comer: '🍽️', canas: '🍺', terraza: '🌇', copas: '🍸', shisha: '💨', fiesta: '🪩' };
const SOL = { latitude: 40.4169, longitude: -3.7035 };

// ---------- datos (con copia guardada por si no hay conexión) ----------
async function datos() {
  const fm = FileManager.local();
  const path = fm.joinPath(fm.cacheDirectory(), 'renta-widget.json');
  try {
    const req = new Request(BASE + 'widget.json'); req.timeoutInterval = 10;
    const j = await req.loadJSON();
    if (j && j.sitios) { fm.writeString(path, JSON.stringify(j)); return j; }
  } catch (e) {}
  if (fm.fileExists(path)) return JSON.parse(fm.readString(path));
  return null;
}
async function ubicacion() {
  try { Location.setAccuracyToThreeKilometers(); return await Location.current(); } catch (e) { return null; }
}
const km = (a, b, c, d) => { const R = 6371, x = (c - a) * Math.PI / 180, y = (d - b) * Math.PI / 180;
  const h = Math.sin(x / 2) ** 2 + Math.cos(a * Math.PI / 180) * Math.cos(c * Math.PI / 180) * Math.sin(y / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); };
const fmtKm = k => k < 1 ? Math.round(k * 1000 / 50) * 50 + ' m' : k.toFixed(1).replace('.', ',') + ' km';
const hoyIso = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10); };

// ---------- qué toca ahora ----------
function franja(now, lluvia) {
  const h = now.getHours() + now.getMinutes() / 60, finde = [0, 5, 6].includes(now.getDay());
  if (h >= 6 && h < 11.5) return { t: 'Para desayunar o un brunch', tipos: ['cafe'] };
  if (h >= 11.5 && h < 16.5) return { t: 'Para comer', tipos: ['comer'] };
  if (h >= 16.5 && h < 20) return { t: 'Para tomar algo', tipos: lluvia ? ['canas', 'cafe', 'copas'] : ['terraza', 'canas', 'cafe'] };
  if (h >= 20 && h < 22.5) return { t: 'Para cenar', tipos: ['comer'] };
  if (h >= 22.5 || h < 2.5) return { t: finde ? 'Para salir' : 'Para una copa', tipos: finde ? ['copas', 'fiesta', 'shisha'] : ['copas', 'shisha'] };
  return { t: 'Para mañana', tipos: ['cafe'] };
}
function elegir(sitios, fr, loc, lluvia, cuantos) {
  const pts = { top: 3, zona: 2, michelin: 2.5, joya: 1.5, nuevo: 1 };
  let c = sitios.filter(s => fr.tipos.includes(s.t) && !(lluvia && s.f));
  c.forEach(s => { s._km = km(loc.latitude, loc.longitude, s.la, s.lo); });
  for (const r of [2, 4, 8, 99]) { const x = c.filter(s => s._km <= r); if (x.length >= cuantos * 3) { c = x; break; } }
  c.forEach(s => { s._sc = (s.s || []).reduce((a, k) => a + (pts[k] || 0), 0) - s._km * 0.6; });
  c.sort((a, b) => b._sc - a._sc);
  const top = c.slice(0, Math.max(8, cuantos * 3));
  // cambia cada hora, pero no en cada refresco
  const now = new Date(), seed = now.getDate() * 24 + now.getHours();
  const out = []; for (let i = 0; i < Math.min(cuantos, top.length); i++) out.push(top[(seed + i * 3) % top.length]);
  return [...new Set(out)];
}
function eventoHoy(eventos, loc) {
  const hoy = hoyIso(), now = new Date(), nm = now.getHours() * 60 + now.getMinutes();
  const ev = (eventos || []).filter(e => e.d <= hoy && e.f >= hoy && (!e.h || (+e.h.slice(0, 2)) * 60 + (+e.h.slice(3, 5)) >= nm - 30));
  ev.forEach(e => { e._km = km(loc.latitude, loc.longitude, e.la, e.lo); });
  return ev.filter(e => e._km <= 6).sort((a, b) => (a._km - b._km) + ((a.h ? 0 : 1) - (b.h ? 0 : 1)) * 2);
}

// ---------- dibujo ----------
function fondo(w) { const g = new LinearGradient(); g.colors = [new Color(C.bg2), new Color(C.bg1)]; g.locations = [0, 1]; w.backgroundGradient = g; }
function txt(stack, s, size, color, weight, lines) {
  const t = stack.addText(s); t.font = weight === 'b' ? Font.boldSystemFont(size) : weight === 'm' ? Font.mediumSystemFont(size) : Font.systemFont(size);
  t.textColor = new Color(color); if (lines) t.lineLimit = lines; t.minimumScaleFactor = 0.75; return t;
}
function cabecera(w, fr) {
  const h = w.addStack(); h.centerAlignContent();
  txt(h, 'Me Renta', 11, C.lime, 'b'); h.addSpacer(5); txt(h, '· ' + fr.t, 11, C.mut, 'm', 1);
}
function sugerencia(stack, s, grande) {
  stack.url = BASE + '?sitio=' + encodeURIComponent(s.n);
  txt(stack, (ICON[s.t] || '📍') + ' ' + s.n, grande ? 17 : 15, C.ink, 'b', 2);
  stack.addSpacer(2);
  txt(stack, [s.c, s.z, s._km != null ? fmtKm(s._km) : ''].filter(Boolean).join(' · '), 11, C.mut, '', 1);
  const sl = (s.s || []).map(k => SELLO[k]).filter(Boolean)[0];
  if (sl) { stack.addSpacer(3); txt(stack, sl, 11, C.lime, 'm', 1); }
}
function tiempoLinea(stack, t) {
  if (!t) return;
  txt(stack, `${t.icono} ${t.max}° / ${t.min}°`, 13, C.ink, 'b', 1);
  txt(stack, t.lluvia >= 40 ? `☔ ${t.lluvia} % lluvia` : t.texto, 11, C.mut, '', 1);
}
function eventoLinea(stack, e) {
  stack.url = e.u || BASE + '?pide=' + encodeURIComponent('eventos hoy');
  txt(stack, '🎟️ ' + e.n, 12, C.ink, 'm', 2);
  txt(stack, [e.h, e.l, e.g ? 'gratis' : ''].filter(Boolean).join(' · '), 10, C.mut, '', 1);
}

async function crear() {
  const fam = config.widgetFamily || 'medium';
  const w = new ListWidget(); fondo(w); w.setPadding(14, 14, 12, 14);
  w.refreshAfterDate = new Date(Date.now() + 30 * 60 * 1000);
  const d = await datos();
  if (!d) { txt(w, 'Me Renta', 12, C.lime, 'b'); w.addSpacer(6); txt(w, 'Sin conexión: vuelve a intentarlo en un rato.', 13, C.ink, 'm'); return w; }
  const loc = (await ubicacion()) || SOL;
  const t = (d.tiempo || []).find(x => x.fecha === hoyIso()) || (d.tiempo || [])[0];
  const lluvia = t && (t.plan === 'interior' || t.lluvia >= 60);
  const fr = franja(new Date(), lluvia);
  const ev = eventoHoy(d.eventos, loc);
  w.url = BASE;

  if (fam === 'small') {
    const [s] = elegir(d.sitios, fr, loc, lluvia, 1);
    cabecera(w, fr); w.addSpacer(8);
    if (s) { const st = w.addStack(); st.layoutVertically(); sugerencia(st, s); }
    w.addSpacer();
    if (t) txt(w, `${t.icono} ${t.max}°${t.lluvia >= 40 ? ' · ☔ ' + t.lluvia + ' %' : ''}`, 11, C.mut, 'm', 1);
    return w;
  }
  if (fam === 'medium') {
    const [s] = elegir(d.sitios, fr, loc, lluvia, 1);
    cabecera(w, fr); w.addSpacer(8);
    const row = w.addStack(); row.topAlignContent();
    const left = row.addStack(); left.layoutVertically(); left.size = new Size(170, 0);
    if (s) sugerencia(left, s);
    row.addSpacer();
    const right = row.addStack(); right.layoutVertically();
    tiempoLinea(right, t);
    if (ev[0]) { right.addSpacer(6); const es = right.addStack(); es.layoutVertically(); es.size = new Size(120, 0); eventoLinea(es, ev[0]); }
    return w;
  }
  // grande (y extra grande en iPad)
  cabecera(w, fr); w.addSpacer(6);
  const top = w.addStack(); top.centerAlignContent();
  if (t) { txt(top, `${t.icono} ${t.max}° / ${t.min}°  ·  ${t.lluvia >= 40 ? '☔ ' + t.lluvia + ' % lluvia' : t.texto}`, 12, C.mut, 'm', 1); }
  w.addSpacer(10);
  elegir(d.sitios, fr, loc, lluvia, 3).forEach((s, i) => {
    const st = w.addStack(); st.layoutVertically(); sugerencia(st, s, i === 0); w.addSpacer(9);
  });
  if (ev.length) {
    txt(w, 'HOY CERCA', 10, C.acc, 'b'); w.addSpacer(3);
    ev.slice(0, 2).forEach(e => { const es = w.addStack(); es.layoutVertically(); eventoLinea(es, e); w.addSpacer(4); });
  }
  w.addSpacer();
  return w;
}

const widget = await crear();
if (config.runsInWidget) Script.setWidget(widget);
else await widget.presentMedium();
Script.complete();
