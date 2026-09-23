/* =====================================================================
   Icons + hand-rolled SVG charts (theme-token colours, no library)
   ===================================================================== */
const ICONS = {
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7z',
  command: 'M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z',
  car: 'M4 17V12l2-5.2A2 2 0 0 1 7.9 5.5h8.2a2 2 0 0 1 1.9 1.3L20 12v5M2.5 17h19M7.5 17v2.5M16.5 17v2.5M4 12h16M7.5 14.5h.01M16.5 14.5h.01',
  plug: 'M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0zM12 17v5',
  sliders: 'M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1M15 4v4M9 10v4M17 16v4',
  grid: 'M12 2v20M7 22l5-14 5 14M8.5 11h7M9.5 16h5M5 6h14',
  pin: 'M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11zM12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  flask: 'M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3M7.5 15h9',
  cog: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1',
  info: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 11v6M12 7.5h.01',
  sun: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4',
  building: 'M4 21V4a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v17M15 9h4a1 1 0 0 1 1 1v11M2 21h20M8 7h3M8 11h3M8 15h3',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  check: 'M5 12.5 10 17.5 19 7',
  x: 'M6 6l12 12M18 6 6 18',
  menu: 'M4 6h16M4 12h16M4 18h16',
  home: 'M3 11 12 3l9 8M5 10v10h14V10M10 20v-5h4v5',
  apartment: 'M5 21V3h9v18M14 8h5v13M8 7h3M8 11h3M8 15h3M2 21h20',
  briefcase: 'M3 8h18v12H3zM9 8V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3M3 13h18',
  bag: 'M5 8h14l1 13H4zM9 8a3 3 0 0 1 6 0',
  commercial: 'M3 21h18M5 21V8l7-4 7 4v13M9 12h2M13 12h2M9 16h2M13 16h2',
  campus: 'M3 10 12 5l9 5-9 5zM7 12.5V17c0 1 2.2 2.5 5 2.5s5-1.5 5-2.5v-4.5',
  hotel: 'M3 18V7M3 13h18v5M21 18v-5a3 3 0 0 0-3-3h-7v3',
  layers: 'M12 3 3 8l9 5 9-5zM3 13l9 5 9-5',
  brain: 'M9 4a3 3 0 0 0-3 3v.5A3 3 0 0 0 4 10.5a3 3 0 0 0 1.5 2.6A3 3 0 0 0 7 18a3 3 0 0 0 5 1V4.5A2.5 2.5 0 0 0 9 4zM15 4a3 3 0 0 1 3 3v.5a3 3 0 0 1 2 3 3 3 0 0 1-1.5 2.6A3 3 0 0 1 17 18a3 3 0 0 1-5 1',
  target: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 12h.01',
  gauge: 'M4 18a9 9 0 1 1 16 0M12 13l4-4M12 13h.01',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'
};
const I = (n, s) => `<svg viewBox="0 0 24 24" width="${s || 18}" height="${s || 18}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICONS[n] || ''}"/></svg>`;

const Charts = (() => {
  let uid = 0;
  const fmtN = v => (Math.round(v * 10) / 10).toString();
  const nice = max => {
    const raw = Math.max(max, 1e-6) / 4, p = Math.pow(10, Math.floor(Math.log10(raw)));
    const c = [1, 2, 2.5, 5, 10].map(m => m * p).find(v => v >= raw);
    return c * 4;
  };

  function line(el, cfgIn) {
    if (el._ch) { el._ch.set(cfgIn); return el._ch; }
    let cfg = cfgIn;
    const id = 'ch' + (++uid), state = { hidden: new Set(), w: 0 };
    el.classList.add('chart');
    function draw() {
      const W = Math.max(300, Math.floor(el.clientWidth) || 640), H = cfg.height || 260, m = { l: 46, r: 16, t: 24, b: 28 };
      state.w = el.clientWidth;
      const iw = W - m.l - m.r, ih = H - m.t - m.b, n = cfg.labels.length;
      const vis = cfg.series.filter(s => !state.hidden.has(s.key));
      const yMax = cfg.yMax || nice(Math.max(...(vis.length ? vis : cfg.series).flatMap(s => s.values)));
      const x = i => m.l + (n < 2 ? 0 : i / (n - 1)) * iw, y = v => m.t + ih - (Math.min(v, yMax) / yMax) * ih;
      let g = '', defs = '';
      for (let k = 0; k <= 4; k++) {
        const v = yMax / 4 * k, yy = y(v);
        g += `<line x1="${m.l}" x2="${W - m.r}" y1="${yy}" y2="${yy}" stroke="rgba(60,48,130,${k ? .11 : .28})" ${k ? 'stroke-dasharray="3 5"' : ''}/><text x="${m.l - 9}" y="${yy + 4}" text-anchor="end">${fmtN(v)}</text>`;
      }
      const tk = Math.min(cfg.xTicks || 5, n - 1);
      for (let k = 0; k <= tk; k++) {
        const i = Math.round(k * (n - 1) / tk);
        g += `<text x="${x(i)}" y="${H - 7}" text-anchor="${k === 0 ? 'start' : k === tk ? 'end' : 'middle'}">${cfg.labels[i]}</text>`;
      }
      if (cfg.unit) g += `<text x="${m.l - 9}" y="${m.t - 14}" text-anchor="end" style="font-weight:800">${cfg.unit}</text>`;
      const path = (vals, step) => vals.map((v, i) => {
        const px = x(i), py = y(v);
        return i === 0 ? `M${px} ${py}` : step ? `H${px}V${py}` : `L${px} ${py}`;
      }).join('');
      // overload region: series above the limit line
      if (cfg.overload && !state.hidden.has(cfg.overload.key)) {
        const s = cfg.series.find(q => q.key === cfg.overload.key), yl = y(cfg.overload.value);
        defs += `<clipPath id="${id}-o"><rect x="${m.l}" y="0" width="${iw}" height="${yl}"/></clipPath>`;
        g += `<path d="${path(s.values)}L${x(n - 1)} ${y(0)}L${x(0)} ${y(0)}Z" fill="rgba(229,72,77,.22)" clip-path="url(#${id}-o)"/>`;
      }
      vis.forEach((s, k) => {
        const p = path(s.values, s.step);
        if (s.area) {
          defs += `<linearGradient id="${id}-g${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${s.color}" stop-opacity=".42"/><stop offset="1" stop-color="${s.color}" stop-opacity="0"/></linearGradient>`;
          g += `<path d="${p}L${x(n - 1)} ${y(0)}L${x(0)} ${y(0)}Z" fill="url(#${id}-g${k})"/>`;
        }
        g += `<path d="${p}" fill="none" stroke="${s.color}" stroke-width="${s.width || 2.2}" stroke-linejoin="round" stroke-linecap="round" ${s.dash ? `stroke-dasharray="${s.dash}"` : ''}/>`;
      });
      vis.forEach(s => { if (!s.noDot && !s.dash) { const li = s.values.length - 1; g += `<circle cx="${x(li)}" cy="${y(s.values[li])}" r="4.5" fill="${s.color}" stroke="#ffffff" stroke-width="2"/>`; } });
      g += `<line id="${id}-v" x1="0" x2="0" y1="${m.t}" y2="${m.t + ih}" stroke="rgba(60,48,130,.45)" stroke-width="1" style="display:none"/>`;
      vis.forEach((s, k) => { g += `<circle id="${id}-d${k}" r="4.5" fill="${s.color}" stroke="#ffffff" stroke-width="2" style="display:none"/>`; });
      const legend = cfg.legend === false ? '' : `<div class="legend" style="margin-bottom:12px">${cfg.series.map(s => `<button type="button" data-k="${s.key}" class="${state.hidden.has(s.key) ? 'off' : ''}" aria-pressed="${!state.hidden.has(s.key)}"><i style="background:${s.color};${s.dash ? 'background:repeating-linear-gradient(90deg,' + s.color + ' 0 5px,transparent 5px 8px)' : ''}"></i>${s.label}</button>`).join('')}</div>`;
      el.innerHTML = `${legend}<div style="position:relative"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${cfg.aria || 'chart'}"><defs>${defs}</defs>${g}<rect id="${id}-hit" x="${m.l}" y="${m.t}" width="${iw}" height="${ih}" fill="transparent"/></svg><div class="tip" id="${id}-tip"></div></div>`;
      el.querySelectorAll('.legend button').forEach(b => b.onclick = () => { const k = b.dataset.k; state.hidden.has(k) ? state.hidden.delete(k) : state.hidden.add(k); draw(); });
      const hit = el.querySelector('#' + id + '-hit'), tip = el.querySelector('#' + id + '-tip'), vl = el.querySelector('#' + id + '-v'), svg = el.querySelector('svg');
      const move = e => {
        const rect = svg.getBoundingClientRect(), px = (e.clientX - rect.left) * (W / rect.width);
        const i = Math.max(0, Math.min(n - 1, Math.round((px - m.l) / iw * (n - 1))));
        vl.setAttribute('x1', x(i)); vl.setAttribute('x2', x(i)); vl.style.display = '';
        vis.forEach((s, k) => { const d = el.querySelector('#' + id + '-d' + k); d.setAttribute('cx', x(i)); d.setAttribute('cy', y(s.values[i])); d.style.display = ''; });
        tip.innerHTML = `<div class="t">${cfg.labels[i]}</div>` + vis.map(s => `<div class="r"><span><i style="background:${s.color}"></i>${s.label}</span><b>${fmtN(s.values[i])} ${cfg.unit || ''}</b></div>`).join('');
        const left = x(i) * (rect.width / W), flip = left > rect.width - 190;
        tip.style.left = (flip ? left - 178 : left + 14) + 'px'; tip.style.top = '6px'; tip.style.opacity = 1;
      };
      const leave = () => { tip.style.opacity = 0; vl.style.display = 'none'; vis.forEach((s, k) => el.querySelector('#' + id + '-d' + k).style.display = 'none'); };
      hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move); hit.addEventListener('pointerleave', leave);
    }
    draw();
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => { if (!el.isConnected) { ro.disconnect(); return; } if (Math.abs(el.clientWidth - state.w) > 4) draw(); });
      ro.observe(el);
    }
    el._ch = { redraw: draw, set: c => { cfg = c; draw(); } };
    return el._ch;
  }

  function spark(vals, o = {}) {
    const w = o.w || 120, h = o.h || 38, c = o.color || '#d5ccf7', pad = 4;
    const mn = Math.min(...vals), mx = Math.max(...vals), rg = mx - mn || 1;
    const pts = vals.map((v, i) => [pad + i / (vals.length - 1) * (w - pad * 2), h - pad - (v - mn) / rg * (h - pad * 2)]);
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('');
    const gid = 'sp' + (++uid), l = pts[pts.length - 1];
    return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c}" stop-opacity=".4"/><stop offset="1" stop-color="${c}" stop-opacity="0"/></linearGradient></defs><path d="${d}L${l[0]} ${h}L${pad} ${h}Z" fill="url(#${gid})"/><path d="${d}" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${l[0]}" cy="${l[1]}" r="3.4" fill="${c}" stroke="#ffffff" stroke-width="1.6"/></svg>`;
  }

  function ring(pct, o = {}) {
    const s = o.size || 84, sw = o.stroke || 9, r = (s - sw) / 2, c = 2 * Math.PI * r, col = o.color || '#d5ccf7';
    return `<svg viewBox="0 0 ${s} ${s}" width="${s}" height="${s}" role="img" aria-label="${o.aria || pct + '%'}"><circle cx="${s / 2}" cy="${s / 2}" r="${r}" fill="none" stroke="rgba(118,96,212,.15)" stroke-width="${sw}"/><circle cx="${s / 2}" cy="${s / 2}" r="${r}" fill="none" stroke="${col}" stroke-width="${sw}" stroke-linecap="round" stroke-dasharray="${c * Math.min(100, pct) / 100} ${c}" transform="rotate(-90 ${s / 2} ${s / 2})"/><text x="50%" y="50%" text-anchor="middle" dominant-baseline="central" style="font-family:var(--f-body);font-weight:800;font-size:${s * .24}px;fill:var(--cream)">${o.label != null ? o.label : Math.round(pct) + '%'}</text></svg>`;
  }

  return { line, spark, ring };
})();
