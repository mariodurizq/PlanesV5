/* Compartir un plan de RENTA: enlace a una página solo con el plan (plan.html#…) e imagen PNG.
   Lo usan index.html (al compartir) y plan.html (al abrir el enlace). */
(function () {
  const BASE = (location.origin + location.pathname).replace(/[^/]*$/, '');
  const CARTO_KEY = 'cb1_4lmn_1_2aac24edf7da67a8627f2599';
  const fmt = m => { m = ((m % 1440) + 1440) % 1440; return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };
  const r5 = x => Math.round(x * 1e5) / 1e5;

  // ---------- datos compactos del plan ----------
  function fromStops(stops, title, day) {
    return {
      v: 1, t: title || 'Plan', d: day || '',
      s: stops.map(s => s._paseo ? {
        p: 1, n: s.n, s: s._start, e: s._end, to: s.toName || '', km: s.km ? Math.round(s.km * 10) / 10 : 0, wm: s.walkMin || 0,
        tm: s.transit ? s.transit.min : 0, sl: s.startLat ? [r5(s.startLat), r5(s.startLon)] : null,
        r: (s.route || []).map(x => [x.n, r5(x.lat), r5(x.lon), x.b || '']), ru: s.routeUrl || '', tu: s.transitUrl || ''
      } : {
        n: s.n, c: s.cd || s.cm || '', z: s.z || '', a: s.addr ? String(s.addr).replace(/, España$/, '').replace(/, \d{5} Madrid$/, '') : '',
        la: s.lat != null ? r5(s.lat) : null, lo: s.lon != null ? r5(s.lon) : null, s: s._start, e: s._end,
        v: s.v || null, nr: s.nr || null, w: s._why || '', p0: s.p || ''
      })
    };
  }
  const b64u = bytes => { let s = ''; bytes.forEach(b => s += String.fromCharCode(b)); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); };
  const unb64u = str => { const s = atob(str.replace(/-/g, '+').replace(/_/g, '/')); return Uint8Array.from(s, c => c.charCodeAt(0)); };
  async function encode(plan) {
    const raw = new TextEncoder().encode(JSON.stringify(plan));
    if (typeof CompressionStream !== 'undefined') {
      try { const z = new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new CompressionStream('deflate-raw'))).arrayBuffer()); return 'z' + b64u(z); } catch (e) {}
    }
    return 'j' + b64u(raw);
  }
  async function decode(code) {
    const kind = code[0], bytes = unb64u(code.slice(1));
    let raw = bytes;
    if (kind === 'z') raw = new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer());
    return JSON.parse(new TextDecoder().decode(raw));
  }
  async function url(plan) { return BASE + 'plan.html#' + await encode(plan); }
  function summary(plan) {
    const lines = plan.s.map(s => s.p ? `${fmt(s.s)} 🚶 ${s.tm ? 'Metro/taxi y paseo por ' + s.to : 'Paseo' + (s.to ? ' hasta ' + s.to : '')}${s.r.length ? ': ' + s.r.slice(0, 4).map(x => x[0]).join(' → ') : ''}`
      : `${fmt(s.s)} ${s.n}${s.c ? ' (' + s.c + ')' : ''}`);
    return `🧭 ${plan.t}\n\n${lines.join('\n')}`;
  }

  // ---------- puntos y líneas para mapa/imagen ----------
  function geometry(plan) {
    const stops = [], walks = [], transit = [], all = [];
    let last = null, n = 0;
    plan.s.forEach(s => {
      if (s.p) {
        const start = s.tm && s.sl ? s.sl : null;
        if (start && last) transit.push([last, start]);
        const line = start ? [start] : (last ? [last] : []);
        s.r.forEach((x, k) => { const ll = [x[1], x[2]]; line.push(ll); all.push(ll); stops.push({ll, label: String.fromCharCode(65 + k), walk: true, name: x[0]}); });
        if (start) all.push(start);
        walks.push({line, open: true}); last = line.length ? line[line.length - 1] : last; return;
      }
      if (s.la == null) return;
      const ll = [s.la, s.lo]; n++; all.push(ll);
      const open = walks.length && walks[walks.length - 1].open ? walks[walks.length - 1] : null;
      if (open) { open.line.push(ll); open.open = false; }
      else if (last) { const far = km(last, ll) > 2.5; if (far) transit.push([last, ll]); else walks.push({line: [last, ll]}); }
      stops.push({ll, label: String(n), walk: false, name: s.n}); last = ll;
    });
    return {stops, walks, transit, all};
  }
  function km(a, b) { const R = 6371, dLa = (b[0] - a[0]) * Math.PI / 180, dLo = (b[1] - a[1]) * Math.PI / 180; const h = Math.sin(dLa / 2) ** 2 + Math.cos(a[0] * Math.PI / 180) * Math.cos(b[0] * Math.PI / 180) * Math.sin(dLo / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); }

  // ---------- imagen PNG ----------
  const wx = (lon, z) => (lon + 180) / 360 * 256 * 2 ** z;
  const wy = (lat, z) => { const s = Math.sin(lat * Math.PI / 180); return (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * 256 * 2 ** z; };
  function loadImg(src) { return new Promise(res => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => res(null); i.src = src; setTimeout(() => res(null), 6000); }); }
  function wrap(ctx, text, maxW) { const words = String(text).split(' '); const out = []; let cur = ''; words.forEach(w => { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }); if (cur) out.push(cur); return out; }
  function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

  async function png(plan, opts) {
    opts = opts || {};
    const W = 1080, PAD = 56, MAPH = 640, F = 'system-ui,-apple-system,"Segoe UI",Roboto,sans-serif';
    const C = {bg: '#0b100e', card: '#141c18', ink: '#f1efe8', mut: '#9aa59e', acc: '#2ec4b6', lime: '#c5e3a0', or: '#e8a24a', line: '#24302b'};
    // medir alto
    const m = document.createElement('canvas').getContext('2d');
    const rows = plan.s.map(s => {
      m.font = `700 34px ${F}`;
      if (s.p) { const pts = s.r.map((x, k) => String.fromCharCode(65 + k) + '. ' + x[0]); m.font = `400 26px ${F}`; const l = pts.length ? wrap(m, pts.join('   '), W - PAD * 2 - 150) : []; return {s, h: 92 + l.length * 36 + (s.tm ? 36 : 0), l}; }
      const nameL = wrap(m, s.n, W - PAD * 2 - 150); return {s, nameL, h: 60 + nameL.length * 42 + 36};
    });
    const H = 250 + MAPH + 40 + rows.reduce((a, r) => a + r.h + 18, 0) + 110;
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    // cabecera
    ctx.fillStyle = C.ink; ctx.font = `900 40px ${F}`; ctx.fillText('RENTA', PAD, 86);
    ctx.fillStyle = C.mut; ctx.font = `500 26px ${F}`; ctx.fillText('· Planes en Madrid', PAD + 150, 86);
    ctx.fillStyle = C.ink; ctx.font = `800 52px ${F}`;
    const tl = wrap(ctx, plan.t.replace(/^Plan · /, 'Plan · '), W - PAD * 2); tl.slice(0, 2).forEach((l, i) => ctx.fillText(l, PAD, 160 + i * 58));
    const first = plan.s[0], lastS = plan.s[plan.s.length - 1];
    ctx.fillStyle = C.acc; ctx.font = `600 30px ui-monospace,Menlo,monospace`; ctx.fillText(`${fmt(first.s)} → ${fmt(lastS.e)}${plan.d ? '  ·  ' + plan.d : ''}`, PAD, 160 + Math.min(2, tl.length) * 58 + 4);
    // mapa
    const my = 250, mx = PAD, mw = W - PAD * 2, mh = MAPH;
    const g = geometry(plan);
    ctx.save(); rr(ctx, mx, my, mw, mh, 28); ctx.clip();
    ctx.fillStyle = '#1b2420'; ctx.fillRect(mx, my, mw, mh);
    let z = 16, proj = null;
    if (g.all.length) {
      const lats = g.all.map(p => p[0]), lons = g.all.map(p => p[1]);
      const minLa = Math.min(...lats), maxLa = Math.max(...lats), minLo = Math.min(...lons), maxLo = Math.max(...lons);
      for (z = 17; z > 8; z--) { if (wx(maxLo, z) - wx(minLo, z) < mw - 140 && wy(minLa, z) - wy(maxLa, z) < mh - 140) break; }
      const cx = (wx(minLo, z) + wx(maxLo, z)) / 2, cy = (wy(minLa, z) + wy(maxLa, z)) / 2;
      const ox = cx - mw / 2, oy = cy - mh / 2;
      proj = ll => [mx + wx(ll[1], z) - ox, my + wy(ll[0], z) - oy];
      // teselas (si el navegador deja leerlas; si no, fondo liso)
      if (opts.tiles !== false) {
        const t0x = Math.floor(ox / 256), t1x = Math.floor((ox + mw) / 256), t0y = Math.floor(oy / 256), t1y = Math.floor((oy + mh) / 256);
        const jobs = [];
        for (let tx = t0x; tx <= t1x; tx++) for (let ty = t0y; ty <= t1y; ty++) {
          const sub = 'abcd'[(tx + ty) & 3];
          jobs.push(loadImg(`https://${sub}.basemaps.cartocdn.com/rastertiles/dark_all/${z}/${tx}/${ty}@2x.png?key=${CARTO_KEY}`).then(img => { if (img) ctx.drawImage(img, mx + tx * 256 - ox, my + ty * 256 - oy, 256, 256); }));
        }
        await Promise.all(jobs);
      }
      // líneas
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      g.walks.forEach(w => { if (w.line.length < 2) return; ctx.strokeStyle = C.acc; ctx.lineWidth = 8; ctx.beginPath(); w.line.forEach((p, i) => { const [x, y] = proj(p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); });
      ctx.setLineDash([14, 14]); g.transit.forEach(t => { ctx.strokeStyle = C.or; ctx.lineWidth = 6; ctx.beginPath(); const a = proj(t[0]), b = proj(t[1]); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }); ctx.setLineDash([]);
      // marcadores
      g.stops.forEach(p => { const [x, y] = proj(p.ll); const r = p.walk ? 17 : 27;
        ctx.fillStyle = p.walk ? C.lime : C.acc; ctx.strokeStyle = p.walk ? '#12201a' : '#fff'; ctx.lineWidth = p.walk ? 3 : 5;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
        ctx.fillStyle = '#0b1d19'; ctx.font = `800 ${p.walk ? 20 : 28}px ${F}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(p.label, x, y + 1); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'; });
    }
    ctx.restore();
    ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.font = `400 18px ${F}`; ctx.fillText('© OpenStreetMap © CARTO', mx + mw - 240, my + mh - 14);
    // paradas
    let y = my + mh + 40, num = 0;
    rows.forEach(({s, h, nameL, l}) => {
      ctx.fillStyle = C.card; rr(ctx, PAD, y, W - PAD * 2, h, 24); ctx.fill();
      ctx.fillStyle = C.acc; ctx.font = `700 28px ui-monospace,Menlo,monospace`; ctx.fillText(fmt(s.s), PAD + 28, y + 50);
      ctx.fillStyle = C.mut; ctx.font = `500 22px ui-monospace,Menlo,monospace`; ctx.fillText(fmt(s.e), PAD + 28, y + 82);
      const tx = PAD + 150;
      if (s.p) {
        ctx.fillStyle = C.ink; ctx.font = `700 32px ${F}`; ctx.fillText('🚶 ' + (s.tm ? 'Paseo por ' + s.to : s.to ? 'Paseo hasta ' + s.to : 'Paseo'), tx, y + 50);
        let yy = y + 86;
        if (s.tm) { ctx.fillStyle = C.or; ctx.font = `500 25px ${F}`; ctx.fillText(`🚇 Metro/taxi unos ${s.tm} min`, tx, yy); yy += 36; }
        ctx.fillStyle = C.mut; ctx.font = `400 26px ${F}`; l.forEach(t => { ctx.fillText(t, tx, yy); yy += 36; });
      } else {
        num++;
        ctx.fillStyle = C.ink; ctx.font = `700 34px ${F}`; nameL.forEach((t, i) => ctx.fillText((i ? '' : num + '. ') + t, tx, y + 50 + i * 42));
        const meta = [s.c, s.z, s.v ? '★ ' + String(Number(s.v).toFixed(1)).replace('.', ',') : '', s.p0 ? s.p0 + ' €' : ''].filter(Boolean).join(' · ');
        ctx.fillStyle = C.mut; ctx.font = `400 25px ${F}`; ctx.fillText(meta.slice(0, 60), tx, y + 50 + nameL.length * 42);
      }
      y += h + 18;
    });
    ctx.fillStyle = C.mut; ctx.font = `500 24px ${F}`; ctx.fillText('Hecho con RENTA · ' + BASE.replace(/^https?:\/\//, ''), PAD, H - 62);
    ctx.font = `400 20px ${F}`; ctx.fillText('Valoraciones: Google Maps · Mapa © OpenStreetMap · © CARTO', PAD, H - 30);
    return await new Promise((res, rej) => { try { cv.toBlob(b => b ? res(b) : rej(new Error('blob')), 'image/png'); } catch (e) { rej(e); } });
  }
  async function pngSafe(plan) { try { return await png(plan); } catch (e) { return await png(plan, {tiles: false}); } }

  async function shareImage(plan) {
    const blob = await pngSafe(plan);
    const file = new File([blob], 'plan-renta.png', {type: 'image/png'});
    if (navigator.canShare && navigator.canShare({files: [file]})) { try { await navigator.share({files: [file], title: plan.t}); return 'shared'; } catch (e) { if (e && e.name === 'AbortError') return 'cancel'; } }
    const u = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = u; a.download = 'plan-renta.png'; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(u), 30000);
    return 'downloaded';
  }

  window.RentaPlanShare = {fromStops, encode, decode, url, summary, geometry, png: pngSafe, shareImage, fmt, BASE};
})();
