/* =====================================================================
   GRID CHARGE — application pages
   Each page: { title, sub, html(), mount() }
   ===================================================================== */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const { T, P, r1 } = GC;
const f1 = v => (Math.round(v * 10) / 10).toFixed(1);
const fmtInt = v => Math.round(v).toLocaleString('en-US');
const dur = m => { const h = Math.floor(m / 60), mm = Math.round(m % 60); return h ? `${h}h ${String(mm).padStart(2, '0')}m` : `${mm}m`; };
const TAG = 'Every vehicle. Every kilowatt. Intelligently connected.';

const COLORS = { grid: '#7660d4', building: '#3f8cf0', solar: '#f2a51c', limit: '#2b2260', ev: '#e0709a', unc: '#e5484d', mint: '#2fb37c' };
const STATUS_CLS = { Charging: 'st-info', Complete: 'st-safe', Completed: 'st-safe', Queued: 'st-lav', Paused: 'st-warn', 'Deadline Missed': 'st-crit', Incomplete: 'st-crit', Met: 'st-safe', 'On track': 'st-safe', 'At risk': 'st-warn', Missed: 'st-crit', Pending: 'st-lav' };
const chip = (t, cls, dot = true) => `<span class="chip ${cls || STATUS_CLS[t] || ''}">${dot ? '<i class="dot"></i>' : ''}${t}</span>`;
const prio = p => p === '—' ? '<span class="tx3">—</span>' : chip(p, p === 'High' ? 'st-warn' : p === 'Medium' ? 'st-info' : 'st-lav', false);
const lvl = l => chip(l, l === 'HIGH' ? 'st-crit' : l === 'MEDIUM' ? 'st-warn' : 'st-safe');
const bar = (pct, cls = '') => `<div class="bar ${cls}"><i style="width:${Math.max(0, Math.min(100, pct))}%"></i></div>`;
const cellbar = (pct, label) => `<div class="cellbar">${bar(pct)}<b>${label != null ? label : Math.round(pct) + '%'}</b></div>`;
const tile = (k, v, cls = '', extra = '') => `<div class="tile ${cls}"><span class="k">${k}</span><span class="v">${v}</span>${extra}</div>`;
const unit = (v, u) => `${v}<span class="u">${u}</span>`;
const card = (title, body, o = {}) => `<section class="card ${o.cls || ''}" ${o.id ? `id="${o.id}"` : ''}>${title || o.right ? `<header class="card-h"><div><div class="card-t">${title || ''}</div>${o.sub ? `<div class="card-s">${o.sub}</div>` : ''}</div>${o.right || ''}</header>` : ''}${body}</section>`;
const seg = (group, opts, cur) => `<div class="seg" role="group" aria-label="${group}">${opts.map(o => `<button type="button" data-act="seg" data-g="${group}" data-v="${o}" class="${o === cur ? 'on' : ''}" aria-pressed="${o === cur}">${o}</button>`).join('')}</div>`;
const pager = (page, pages, group) => `<div class="pager">${page > 1 ? '' : ''}<button type="button" data-act="page" data-g="${group}" data-v="${page - 1}" ${page <= 1 ? 'disabled' : ''} aria-label="Previous page">‹</button>${Array.from({ length: pages }, (_, i) => `<button type="button" data-act="page" data-g="${group}" data-v="${i + 1}" class="${i + 1 === page ? 'on' : ''}">${i + 1}</button>`).join('')}<button type="button" data-act="page" data-g="${group}" data-v="${page + 1}" ${page >= pages ? 'disabled' : ''} aria-label="Next page">›</button></div>`;

/* persistent UI state */
const S = {
  range: '6H', horizon: '15M',
  fleet: { q: '', status: 'All', soc: 'any', target: 'any', urg: 'any', comp: 'any', pow: 'any', page: 1, open: null },
  sess: { q: '', status: 'All', page: 1, sel: 'S-1024' },
  opt: { sel: 0 },
  site: { type: 'Office', grid: 250, building: 195, solar: 40, evs: 20, energy: 24, hours: 8, done: true, err: '' },
  wi: { limit: 240, evs: 70, solar: 150, bld: 100, maxP: 7.2 }
};

const Pages = {};

/* ============================ COMMAND CENTER ============================ */
Pages.command = {
  title: 'Command Center', sub: TAG,
  html() {
    const s = GC.snap(), fs = GC.fleetStats(), st = GC.status(), ds = GC.stats;
    const demand = s.building + s.ev, share = Math.round(s.solar / demand * 100);
    const solarUsed = 96.8, solarUtil = Math.round(solarUsed / s.solar * 100);
    const pct = Math.round(fs.Charging / fs.total * 100);
    const capCls = st.key === 'safe' ? '' : st.key === 'constrained' ? 'warn' : 'crit';
    const fleet4 = GC.FLEET.slice(0, 4);
    return `
    <p class="lead-p">What is happening across the entire charging ecosystem — vehicles, building, solar and grid — right now, and what the controller is about to do next.</p>
    <div class="grid">
      <div class="c3 card kpi t-lav">
        <div class="k">${I('car')}Active Charging</div>
        <div class="v v-xl">${fs.Charging}<span class="u"> / ${fs.total}</span></div>
        <div class="note">vehicles charging intelligently</div>
        <div class="aside">${Charts.ring(pct, { size: 66, stroke: 8, color: COLORS.grid })}</div>
        <div class="foot">${bar(pct)}</div>
      </div>
      <div class="c3 card kpi t-sky">
        <div class="k">${I('bolt')}EV Charging Power</div>
        <div class="v v-xl">${unit(f1(s.ev), 'kW')}</div>
        <div class="note">Within allocation · Balanced load</div>
        <div class="foot">${Charts.spark(GC.sparkOf('ev', 30), { w: 250, h: 40, color: COLORS.building })}</div>
      </div>
      <div class="c3 card kpi t-sun">
        <div class="k">${I('sun')}Solar Generation</div>
        <div class="v v-xl">${unit(f1(s.solar), 'kW')}</div>
        <div class="note">${share}% renewable share of demand</div>
        <div class="aside">${Charts.ring(share, { size: 66, stroke: 8, color: COLORS.solar })}</div>
        <div class="foot">${bar(share, 'amber')}</div>
      </div>
      <div class="c3 card kpi t-mint">
        <div class="k">${I('plug')}Energy Delivered</div>
        <div class="v v-xl">${unit(f1(fs.delivered), 'kWh')}</div>
        <div class="note">${fs.Complete} sessions complete today</div>
        <div class="foot">${Charts.spark(GC.sparkOf('grid', 40).map((v, i) => v * .4 + i * 3), { w: 250, h: 40, color: COLORS.mint })}</div>
      </div>

      ${card('Energy Flow', `
        <div class="flowbox" style="height:390px">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" style="position:absolute;inset:0;width:100%;height:100%" aria-hidden="true">
            <line class="flow" x1="50" y1="14" x2="50" y2="50" stroke="${COLORS.solar}" stroke-width="3" vector-effect="non-scaling-stroke" stroke-linecap="round"/>
            <line class="flow" x1="14" y1="50" x2="50" y2="50" stroke="${COLORS.grid}" stroke-width="3" vector-effect="non-scaling-stroke" stroke-linecap="round"/>
            <line class="flow" x1="86" y1="50" x2="50" y2="50" stroke="${COLORS.building}" stroke-width="3" vector-effect="non-scaling-stroke" stroke-linecap="round" style="animation-direction:reverse"/>
            <line class="flow" x1="50" y1="50" x2="50" y2="86" stroke="${COLORS.ev}" stroke-width="3.4" vector-effect="non-scaling-stroke" stroke-linecap="round"/>
          </svg>
          <div class="fnode solar" style="left:50%;top:11%"><span class="k">Solar Generation</span><span class="v">${unit(f1(s.solar), 'kW')}</span></div>
          <div class="fnode" style="left:15%;top:50%"><span class="k">Grid Import</span><span class="v">${unit(f1(s.gridImport), 'kW')}</span></div>
          <div class="fnode bld" style="left:85%;top:50%"><span class="k">Building Demand</span><span class="v">${unit(f1(s.building), 'kW')}</span></div>
          <div class="fctrl" style="left:50%;top:50%"><span class="n">SMART CONTROLLER</span><span class="n2">LOOK-AHEAD V5</span><span class="s">${chip(st.key === 'safe' ? 'BALANCED' : st.key === 'constrained' ? 'LIMITING' : 'PROTECTING', st.cls)}</span><span class="ok">${s.violations ? '! ' + s.violations : '✓ 0'} GRID LIMIT VIOLATIONS</span></div>
          <div class="fnode ev" style="left:50%;top:89%"><span class="k">EV Charging</span><span class="v">${unit(f1(s.ev), 'kW')}</span></div>
        </div>`, { cls: 'c8', sub: 'Solar + grid feed the controller, which decides how much reaches the vehicles.' })}

      ${card('Grid Status', `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
          <div><div class="v v-xl" style="color:${st.key === 'safe' ? 'var(--mint)' : st.key === 'constrained' ? 'var(--gold)' : 'var(--coral)'}">${st.key === 'safe' ? 'SAFE' : st.key === 'constrained' ? 'WATCH' : 'ALERT'}</div><div class="k" style="margin-top:8px">${s.util}% Grid utilization</div></div>
          ${Charts.ring(s.util, { size: 76, stroke: 9, color: st.key === 'safe' ? COLORS.mint : st.key === 'constrained' ? '#f0a01c' : COLORS.unc })}
        </div>
        <div class="capbar"><div class="fill ${capCls}" style="width:${s.util}%"></div><span class="mk" style="left:${Math.min(94, Math.max(6, s.util))}%">${f1(s.gridImport)} kW</span></div>
        <div class="capbar-l"><span>0 kW</span><span>${GC.LIMIT} kW</span></div>
        <div class="stat-list" style="margin-top:12px">
          <div class="stat"><span class="k">Current import</span><span class="v v-md">${unit(f1(s.gridImport), 'kW')}</span></div>
          <div class="stat"><span class="k">Available headroom</span><span class="v v-md">${unit(f1(s.headroom), 'kW')}</span></div>
          <div class="stat"><span class="k">Controlled / uncontrolled overload</span><span class="v v-md">${f1(ds.ctrlOverload)} <span class="tx3">/</span> <span style="color:var(--coral)">${f1(ds.uncOverload)}</span><span class="u">kW</span></span></div>
          <div class="stat"><span class="k">Grid-safe intervals</span><span class="v v-md">${ds.safeIntervals} / ${ds.totalIntervals}</span></div>
        </div>
        <div style="margin-top:12px">${chip(st.msg, st.cls)}</div>`, { cls: 'c4 t-mint' })}

      ${card('Energy Profile', `<div id="ep-chart"></div>`, { cls: 'c8', sub: 'Demand against grid capacity, streamed from the backend.', right: seg('range', ['1H', '6H', '12H', '24H'], S.range) })}

      ${card('Forecast Monitor', `<div id="fc-body"></div>`, { cls: 'c4 t-sky', sub: 'Grid Charge looks ahead — it does not only react.', right: seg('horizon', GC.FORECAST.map(f => f.k), S.horizon) })}

      ${card('Optimization Engine', `
        <div style="display:flex;gap:22px;flex-wrap:wrap;align-items:flex-end;justify-content:space-between">
          <div><div class="v v-xl">${fmtInt(GC.OPT.decisions)}</div><div class="k" style="margin-top:8px">Intelligent decisions recorded</div></div>
          ${chip('Grid constraints ✓ all satisfied', 'st-safe', false)}
        </div>
        <div class="stat-list" style="margin-top:14px">
          <div class="stat"><span class="k">Strategy</span><b>LOOK-AHEAD V5</b></div>
          <div class="stat"><span class="k">Planning horizon</span><b>${GC.OPT.horizon}</b></div>
          <div class="stat"><span class="k">Optimization interval</span><b>${GC.OPT.interval}</b></div>
        </div>
        <p class="tx2" style="margin:14px 0 18px;font-size:13.5px;line-height:1.6">Balancing departure targets with available solar, building demand, grid capacity, battery SOC, and future congestion.</p>
        <a class="link" href="#/optimization">View decision log ${I('arrow')}</a>`, { cls: 'c6 t-lav' })}

      ${card('Renewable Contribution', `
        <div style="display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center">
          <div style="display:grid;gap:10px;justify-items:center">${Charts.ring(share, { size: 112, stroke: 12, color: COLORS.solar, aria: 'Renewable share' })}<span class="k">Renewable share</span></div>
          <div class="stat-list">
            <div class="stat"><span class="k">Solar available</span><span class="v v-md">${unit(f1(s.solar), 'kW')}</span></div>
            <div class="stat"><span class="k">Solar used</span><span class="v v-md">${unit(f1(solarUsed), 'kW')}</span></div>
            <div class="stat"><span class="k">Renewable share</span><span class="v v-md">${share}%</span></div>
            <div class="stat"><span class="k">Solar utilization</span><span class="v v-md">${solarUtil}%</span></div>
          </div>
        </div>
        <p class="tx2" style="margin-top:14px;font-size:13px">Every kilowatt of solar the controller soaks up is a kilowatt the grid does not have to supply.</p>`, { cls: 'c6' })}

      ${card('Fleet at a Glance', `
        <div class="tiles" style="margin-bottom:16px">
          ${tile('Charging', fs.Charging, 'hl')}${tile('Complete', fs.Complete, 'ok')}${tile('Queued', fs.Queued)}${tile('Paused', fs.Paused, 'warn')}
        </div>
        <div class="tbl-wrap"><table><thead><tr><th>Vehicle</th><th>Status</th><th>Battery / Target</th><th>Charging power</th><th>Departure</th><th>Details</th></tr></thead><tbody>
          ${fleet4.map(e => `<tr class="click" data-act="open-ev" data-id="${e.id}"><td class="mono"><b>${e.id}</b></td><td>${chip(e.status)}</td><td>${e.soc}% <span class="tx3">/</span> ${e.target}%</td><td>${f1(e.power)} kW</td><td class="mono">${T(e.dep)}</td><td><span class="link">View ${I('arrow')}</span></td></tr>`).join('')}
        </tbody></table></div>
        <div style="margin-top:16px"><a class="link" href="#/fleet">View full fleet ${I('arrow')}</a></div>`, { cls: 'c8' })}

      ${card('System Activity', `<div class="tl">${GC.ACTIVITY.map(a => `<div class="tl-i ${a.tone}"><span class="t">${a.t}</span><span class="d"><i></i></span><p>${a.a}<em>${a.b}</em></p></div>`).join('')}</div>`, { cls: 'c4 t-peach' })}
    </div>`;
  },
  mount() { Pages.command.drawProfile(); Pages.command.drawForecast(); },
  drawProfile() {
    const pts = GC.profile(S.range);
    Charts.line($('#ep-chart'), {
      labels: pts.map(p => p.t), unit: 'kW', height: 290, xTicks: 6, aria: 'Energy profile',
      series: [
        { key: 'grid', label: 'Grid Import', color: COLORS.grid, values: pts.map(p => p.grid), area: true },
        { key: 'building', label: 'Building Demand', color: COLORS.building, values: pts.map(p => p.building) },
        { key: 'solar', label: 'Solar Generation', color: COLORS.solar, values: pts.map(p => p.solar), area: true },
        { key: 'limit', label: 'Grid Limit', color: COLORS.limit, values: pts.map(p => p.limit), dash: '6 6', width: 1.8 }
      ]
    });
  },
  drawForecast() {
    const f = GC.FORECAST.find(x => x.k === S.horizon), n = f.level === 'LOW' ? 1 : f.level === 'MEDIUM' ? 2 : 3;
    $('#fc-body').innerHTML = `
      <div class="k" style="color:var(--amber)">${f.h}</div>
      <div class="stat-list" style="margin-top:6px">
        <div class="stat"><span class="k">Predicted building demand</span><span class="v v-lg">${unit(f1(f.building), 'kW')}</span></div>
        <div class="stat"><span class="k">Available future capacity</span><span class="v v-lg">${unit(f1(f.capacity), 'kW')}</span></div>
      </div>
      <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:center"><span class="k">Forecast congestion</span>${lvl(f.level)}</div>
      <div class="cong" style="margin-top:10px">${[1, 2, 3].map(i => `<i class="${i <= n ? 'on' + n : ''}"></i>`).join('')}</div>
      <div style="margin-top:18px">${Charts.spark(GC.FORECAST.map(x => x.capacity), { w: 300, h: 46, color: COLORS.mint })}<div class="capbar-l" style="margin-top:4px"><span>Available capacity by horizon</span><span>15M → 6H</span></div></div>`;
  }
};

/* ============================ EV FLEET ============================ */
function fleetFiltered() {
  const f = S.fleet, q = f.q.trim().toLowerCase();
  return GC.FLEET.filter(e => {
    if (q && !(e.id.toLowerCase().includes(q) || e.status.toLowerCase().includes(q) || e.id.replace('EV-', '').replace(/^0+/, '') === q)) return false;
    if (f.status !== 'All' && e.status !== f.status) return false;
    if (f.soc === '<40' && !(e.soc < 40)) return false;
    if (f.soc === '40-70' && !(e.soc >= 40 && e.soc <= 70)) return false;
    if (f.soc === '>70' && !(e.soc > 70)) return false;
    if (f.target !== 'any' && e.target !== +f.target) return false;
    if (f.urg !== 'any' && e.urgency !== f.urg) return false;
    if (f.comp === '<50' && !(e.completion < 50)) return false;
    if (f.comp === '50-80' && !(e.completion >= 50 && e.completion <= 80)) return false;
    if (f.comp === '>80' && !(e.completion > 80)) return false;
    if (f.pow === '0' && e.power !== 0) return false;
    if (f.pow === '<5' && !(e.power > 0 && e.power < 5)) return false;
    if (f.pow === '5-6.5' && !(e.power >= 5 && e.power <= 6.5)) return false;
    if (f.pow === '>6.5' && !(e.power > 6.5)) return false;
    return true;
  });
}
const opt = (v, l, cur) => `<option value="${v}" ${String(cur) === String(v) ? 'selected' : ''}>${l}</option>`;
Pages.fleet = {
  title: 'EV Fleet', sub: TAG,
  html() {
    const fs = GC.fleetStats(), f = S.fleet;
    return `
    <p class="lead-p">Monitor battery status, charging power, energy requirements, and departure urgency across every connected vehicle.</p>
    <div class="tiles">
      ${tile('Total EVs', fs.total, 'hl')}${tile('Charging', fs.Charging)}${tile('Complete', fs.Complete, 'ok')}${tile('Queued', fs.Queued)}${tile('Paused', fs.Paused, 'warn')}
    </div>
    <div class="tiles">
      ${tile('Average SOC', fs.avgSoc + '%')}${tile('Average completion', fs.avgCompletion + '%')}${tile('Required energy', unit(fmtInt(fs.required), 'kWh'))}${tile('Delivered energy', unit(fmtInt(fs.delivered), 'kWh'))}
    </div>
    ${card('', `
      <div class="filters">
        <div class="field"><label for="fq">Search EV ID</label><div class="search">${I('search')}<input id="fq" class="inp" type="search" placeholder="e.g. EV-023 or 23" value="${f.q}" data-bind="fleet.q" autocomplete="off"></div></div>
        <div class="field"><label for="fst">Charging status</label><select id="fst" class="sel" data-bind="fleet.status">${['All', 'Charging', 'Complete', 'Queued', 'Paused'].map(v => opt(v, v === 'All' ? 'All statuses' : v, f.status)).join('')}</select></div>
        <div class="field"><label for="fsoc">Current SOC</label><select id="fsoc" class="sel" data-bind="fleet.soc">${opt('any', 'Any SOC', f.soc)}${opt('<40', 'Below 40%', f.soc)}${opt('40-70', '40 – 70%', f.soc)}${opt('>70', 'Above 70%', f.soc)}</select></div>
        <div class="field"><label for="ftg">Target SOC</label><select id="ftg" class="sel" data-bind="fleet.target">${opt('any', 'Any target', f.target)}${[80, 85, 90, 100].map(v => opt(v, v + '%', f.target)).join('')}</select></div>
        <div class="field"><label for="fug">Departure urgency</label><select id="fug" class="sel" data-bind="fleet.urg">${opt('any', 'Any urgency', f.urg)}${['High', 'Medium', 'Low'].map(v => opt(v, v + (v === 'High' ? ' (< 2 h)' : v === 'Medium' ? ' (2 – 4 h)' : ' (> 4 h)'), f.urg)).join('')}</select></div>
        <div class="field"><label for="fcp">Completion</label><select id="fcp" class="sel" data-bind="fleet.comp">${opt('any', 'Any completion', f.comp)}${opt('<50', 'Below 50%', f.comp)}${opt('50-80', '50 – 80%', f.comp)}${opt('>80', 'Above 80%', f.comp)}</select></div>
        <div class="field"><label for="fpw">Charging power</label><select id="fpw" class="sel" data-bind="fleet.pow">${opt('any', 'Any power', f.pow)}${opt('0', 'Not charging (0 kW)', f.pow)}${opt('<5', 'Below 5 kW', f.pow)}${opt('5-6.5', '5 – 6.5 kW', f.pow)}${opt('>6.5', 'Above 6.5 kW', f.pow)}</select></div>
      </div>
      <div id="fleet-table" style="margin-top:18px"></div>`, { cls: 'plain' })}`;
  },
  mount() { Pages.fleet.table(); if (S.fleet.open) { openEV(S.fleet.open); S.fleet.open = null; } },
  table() {
    const f = S.fleet, list = fleetFiltered(), per = 12, pages = Math.max(1, Math.ceil(list.length / per));
    f.page = Math.min(f.page, pages);
    const rows = list.slice((f.page - 1) * per, f.page * per);
    $('#fleet-table').innerHTML = `<div class="tbl-wrap"><table><thead><tr>
      <th>EV ID</th><th>Status</th><th>Current SOC</th><th>Target SOC</th><th>Battery capacity</th><th>Energy required</th><th>Charging power</th><th>Maximum power</th><th>Arrival</th><th>Departure</th><th>Completion</th><th>Priority</th><th>Details</th></tr></thead><tbody>
      ${rows.length ? rows.map(e => `<tr class="click" data-act="open-ev" data-id="${e.id}"><td class="mono"><b>${e.id}</b></td><td>${chip(e.status)}</td><td>${cellbar(e.soc)}</td><td>${e.target}%</td><td>${e.cap} kWh</td><td>${f1(e.required)} kWh</td><td>${e.power ? f1(e.power) + ' kW' : '<span class="tx3">0.0 kW</span>'}</td><td>${f1(e.max)} kW</td><td class="mono">${T(e.arr)}</td><td class="mono">${T(e.dep)}</td><td>${cellbar(e.completion)}</td><td>${prio(e.priority)}</td><td><span class="link">View ${I('arrow')}</span></td></tr>`).join('') : `<tr><td colspan="13" class="empty">No vehicles match these filters. Clear a filter to see the full fleet.</td></tr>`}
      </tbody></table></div>
      <div class="tbl-foot"><span>Showing ${list.length ? (f.page - 1) * per + 1 : 0}–${Math.min(list.length, f.page * per)} of ${list.length} vehicles</span>${pages > 1 ? pager(f.page, pages, 'fleet') : ''}</div>`;
  }
};

function openEV(id) {
  const e = GC.by(id), h = GC.history(e), oh = GC.optHistory(e);
  const wrap = $('#drawer');
  wrap.innerHTML = `<div class="drawer-bg" data-act="close-drawer"></div>
  <aside class="drawer" role="dialog" aria-modal="true" aria-label="${e.id} details">
    <div class="drawer-h"><div><div class="k">EV detail</div><h2>${e.id}</h2><div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">${chip(e.status)}${prio(e.priority)}<span class="chip">Session ${e.sessionId}</span></div></div>
      <button class="x-btn" type="button" data-act="close-drawer" aria-label="Close details">${I('x')}</button></div>
    <div class="tiles">
      ${tile('Current SOC', e.soc + '%', 'hl')}${tile('Target SOC', e.target + '%')}${tile('Battery capacity', unit(e.cap, 'kWh'))}${tile('Energy required', unit(f1(e.required), 'kWh'))}
      ${tile('Allocated power', unit(f1(e.power), 'kW'))}${tile('Maximum power', unit(f1(e.max), 'kW'))}${tile('Departure', T(e.dep))}${tile('Completion', e.completion + '%')}
    </div>
    <div class="dsec"><span class="card-t">Charging history</span>${h.t.length ? '<div id="dr-p"></div>' : '<p class="tx2">Queued — waiting for the optimizer to allocate power.</p>'}</div>
    <div class="dsec"><span class="card-t">SOC history</span>${h.t.length ? '<div id="dr-s"></div>' : '<p class="tx2">No SOC samples yet.</p>'}</div>
    <div class="dsec"><span class="card-t">Optimization history</span>
      ${oh.length ? `<div class="tbl-wrap"><table><thead><tr><th>Timestamp</th><th>Allocated power</th><th>Priority</th><th>Forecast conditions</th><th>Decision reason</th></tr></thead><tbody>${oh.map(r => `<tr><td class="mono">${r.t}</td><td>${f1(r.p)} kW</td><td>${r.prio.toFixed(2)}</td><td class="wrap">${r.cond}</td><td class="wrap">${r.reason}</td></tr>`).join('')}</tbody></table></div>` : '<p class="tx2">No decisions recorded for this vehicle yet.</p>'}
    </div>
  </aside>`;
  wrap.classList.add('open'); document.body.style.overflow = 'hidden';
  if (h.t.length) {
    Charts.line($('#dr-p'), { labels: h.t, unit: 'kW', height: 200, legend: false, xTicks: 4, aria: 'Charging power history', yMax: 8, series: [{ key: 'p', label: 'Charging power', color: COLORS.ev, values: h.p, area: true, step: true }] });
    Charts.line($('#dr-s'), { labels: h.t, unit: '%', height: 200, legend: false, xTicks: 4, aria: 'SOC history', yMax: 100, series: [{ key: 's', label: 'SOC', color: COLORS.mint, values: h.soc, area: true }] });
  }
  $('.x-btn', wrap).focus();
}

/* ============================ CHARGING SESSIONS ============================ */
function sessFiltered() {
  const f = S.sess, q = f.q.trim().toLowerCase();
  return GC.FLEET.filter(e => (f.status === 'All' || e.sessionStatus === f.status) && (!q || e.id.toLowerCase().includes(q) || e.sessionId.toLowerCase().includes(q)));
}
Pages.sessions = {
  title: 'Charging Sessions', sub: TAG,
  html() {
    const s = GC.sessionStats(), f = S.sess;
    return `
    <p class="lead-p">The EV Fleet page describes the state of vehicles. This page describes individual charging events — what happened during each session.</p>
    <div class="tiles">
      ${tile('Connected vehicles', s.connected, 'hl')}${tile('Active sessions', s.active)}${tile('Completed today', s.completed, 'ok', s.missed ? `<span class="tx2" style="font-size:12px">${s.missed} missed their deadline</span>` : '')}${tile('Queued', s.queued)}
    </div>
    <div class="tiles">
      ${tile('Energy delivered', unit(f1(s.energy), 'kWh'))}${tile('Average session duration', dur(s.avgDur * 60))}${tile('Average charging power', unit(f1(s.avgPower), 'kW'))}${tile('Average completion', s.avgCompletion + '%')}
    </div>
    ${card('Session log', `
      <div class="filters" style="grid-template-columns:minmax(220px,1fr) auto;align-items:end">
        <div class="field"><label for="sq">Search session or EV</label><div class="search">${I('search')}<input id="sq" class="inp" type="search" placeholder="S-1024 or EV-024" value="${f.q}" data-bind="sess.q" autocomplete="off"></div></div>
        <div style="overflow-x:auto;padding-bottom:2px">${seg('sstatus', ['All', 'Charging', 'Completed', 'Queued', 'Paused', 'Deadline Missed', 'Incomplete'], f.status)}</div>
      </div>
      <div id="sess-table" style="margin-top:18px"></div>`, { cls: 'plain' })}
    <div id="sess-detail"></div>`;
  },
  mount() {
    const list = sessFiltered(), i = list.findIndex(e => e.sessionId === S.sess.sel);
    if (i >= 0) S.sess.page = Math.floor(i / 10) + 1;
    Pages.sessions.table(); Pages.sessions.detail();
  },
  table() {
    const f = S.sess, list = sessFiltered(), per = 10, pages = Math.max(1, Math.ceil(list.length / per));
    f.page = Math.min(f.page, pages);
    const rows = list.slice((f.page - 1) * per, f.page * per);
    $('#sess-table').innerHTML = `<div class="tbl-wrap"><table><thead><tr><th>Session ID</th><th>EV ID</th><th>Arrival</th><th>Departure</th><th>Duration</th><th>Initial SOC</th><th>Target SOC</th><th>Energy required</th><th>Energy delivered</th><th>Current power</th><th>Status</th><th>Completion</th></tr></thead><tbody>
      ${rows.length ? rows.map(e => `<tr class="click ${e.sessionId === f.sel ? 'sel' : ''}" data-act="sel-session" data-id="${e.sessionId}"><td class="mono"><b>${e.sessionId}</b></td><td class="mono">${e.id}</td><td class="mono">${T(e.arr)}</td><td class="mono">${T(e.dep)}</td><td>${dur(e.dep - e.arr)}</td><td>${Math.round(e.init)}%</td><td>${e.target}%</td><td>${f1(e.sessionReq)} kWh</td><td>${f1(e.delivered)} kWh</td><td>${e.power ? f1(e.power) + ' kW' : '<span class="tx3">—</span>'}</td><td>${chip(e.sessionStatus)}</td><td>${cellbar(e.completion)}</td></tr>`).join('') : `<tr><td colspan="12" class="empty">No sessions match. Try another status, or clear the search.</td></tr>`}
      </tbody></table></div>
      <div class="tbl-foot"><span>${list.length} sessions · select a row to inspect it</span>${pages > 1 ? pager(f.page, pages, 'sess') : ''}</div>`;
  },
  detail() {
    const e = GC.FLEET.find(x => x.sessionId === S.sess.sel) || GC.FLEET[23], d = GC.sessionDetail(e), h = GC.history(e);
    const started = e.arr, ok = { arr: true, con: e.status !== 'Queued', opt: e.status !== 'Queued', chg: e.status !== 'Queued', adj: e.status === 'Charging' || e.status === 'Complete' || e.status === 'Paused', end: e.status === 'Complete' };
    const step = (n, k, sm, time, on) => `<div class="step ${on ? '' : 'pend'}"><span class="n">${on ? n : ''}</span><div><b>${k}</b><small>${sm}</small></div><time>${time}</time></div>`;
    $('#sess-detail').innerHTML = card(`Session detail · ${e.id}`, `
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin:-4px 0 18px">${chip(e.sessionStatus)}<span class="chip">${e.sessionId}</span>${chip('Deadline ' + d.deadline, STATUS_CLS[d.deadline])}</div>
      <div class="tiles">
        ${tile('Arrival', T(e.arr))}${tile('Departure', T(e.dep))}${tile('Initial SOC', Math.round(e.init) + '%')}${tile('Target SOC', e.target + '%')}${tile('Energy required', unit(f1(e.sessionReq), 'kWh'), 'hl')}${tile('Energy delivered', unit(f1(e.delivered), 'kWh'), 'ok')}
      </div>
      <div class="grid" style="margin-top:22px">
        <div class="c4 keep card plain"><div class="card-t" style="margin-bottom:16px">Session timeline</div><div class="steps">
          ${step(1, 'Arrived', 'Vehicle detected at the site', T(started), ok.arr)}
          ${step(2, 'Connected', 'Plug handshake complete', T(started + 3), ok.con)}
          ${step(3, 'Optimization', 'Priority scored by V5 look-ahead', T(started + 8), ok.opt)}
          ${step(4, 'Charging', 'Power allocated within grid limit', T(started + 15), ok.chg)}
          ${step(5, 'Power adjustments', ok.adj ? d.adjustments + ' re-allocations so far' : 'Waiting for allocation', ok.adj ? T(Math.min(GC.NOW, e.dep)) : '—', ok.adj)}
          ${step(6, 'Completed / Departed', e.status === 'Complete' ? (e.missed ? 'Departed below target SOC' : 'Target SOC reached') : 'In progress', e.status === 'Complete' ? T(d.fin) : '—', ok.end)}
        </div></div>
        <div class="c8 keep card plain" style="display:grid;gap:18px">
          <div><div class="card-t" style="margin-bottom:10px">Charging power vs time</div>${h.t.length ? '<div id="sd-p"></div>' : '<p class="tx2">Queued — no power delivered yet.</p>'}</div>
          <div><div class="card-t" style="margin-bottom:10px">SOC vs time</div>${h.t.length ? '<div id="sd-s"></div>' : '<p class="tx2">No SOC samples yet.</p>'}</div>
        </div>
      </div>
      <div class="grid" style="margin-top:18px">
        <div class="c4 keep card plain"><div class="card-t" style="margin-bottom:14px">Energy delivered</div>
          <div class="v v-lg">${unit(f1(e.delivered), 'kWh')} <span class="tx3" style="font-size:.6em;font-weight:600">of ${f1(e.sessionReq)}</span></div>
          <div style="margin-top:12px">${bar(e.sessionReq ? e.delivered / e.sessionReq * 100 : 0, 'mint')}</div><div class="capbar-l" style="margin-top:6px"><span>0</span><span>${e.sessionReq ? Math.round(e.delivered / e.sessionReq * 100) : 0}% of need</span></div></div>
        <div class="c4 keep card plain"><div class="card-t" style="margin-bottom:14px">Solar vs grid contribution</div>
          <div style="display:flex;height:16px;border-radius:99px;overflow:hidden;background:rgba(255,255,255,.1)"><i style="width:${d.solarShare * 100}%;background:${COLORS.solar}"></i><i style="width:${d.gridShare * 100}%;background:${COLORS.grid}"></i></div>
          <div class="stat-list" style="margin-top:10px"><div class="stat"><span class="k"><span style="color:${COLORS.solar}">●</span> Solar</span><b>${f1(d.solarE)} kWh · ${Math.round(d.solarShare * 100)}%</b></div><div class="stat"><span class="k"><span style="color:${COLORS.grid}">●</span> Grid</span><b>${f1(d.gridE)} kWh · ${Math.round(d.gridShare * 100)}%</b></div></div></div>
        <div class="c4 keep card plain"><div class="card-t" style="margin-bottom:6px">Outlook</div><div class="stat-list">
          <div class="stat"><span class="k">Time remaining</span><b>${e.status === 'Charging' ? dur(Math.max(0, e.dep - GC.NOW)) : e.status === 'Complete' ? '—' : e.status === 'Queued' ? dur(e.dep - GC.NOW) : dur(Math.max(0, e.dep - GC.NOW))}</b></div>
          <div class="stat"><span class="k">Estimated completion</span><b>${e.status === 'Charging' ? T(d.eta) : e.status === 'Complete' ? T(d.fin) : '—'}</b></div>
          <div class="stat"><span class="k">Deadline status</span>${chip(d.deadline, STATUS_CLS[d.deadline])}</div></div></div>
      </div>`, { cls: '' });
    if (h.t.length) {
      Charts.line($('#sd-p'), { labels: h.t, unit: 'kW', height: 190, legend: false, xTicks: 4, yMax: 8, aria: 'Charging power vs time', series: [{ key: 'p', label: 'Charging power', color: COLORS.ev, values: h.p, area: true, step: true }] });
      Charts.line($('#sd-s'), { labels: h.t, unit: '%', height: 190, legend: false, xTicks: 4, yMax: 100, aria: 'SOC vs time', series: [{ key: 's', label: 'SOC', color: COLORS.mint, values: h.soc, area: true }] });
    }
  }
};

/* ============================ OPTIMIZATION ============================ */
Pages.optimization = {
  title: 'Optimization Engine', sub: 'Forecast-aware charging decisions for a safe and balanced local grid.',
  html() {
    const o = GC.OPT;
    return `
    <p class="lead-p">This page exposes the intelligence behind Grid Charge. Every allocation is scored, recorded, and explained — nothing is a black box.</p>
    <div class="tiles">
      ${tile('Optimization version', o.version, 'hl')}${tile('Strategy', o.strategy)}${tile('Planning horizon', o.horizon)}${tile('Optimization interval', o.interval)}${tile('Grid constraint', '✓ SATISFIED', 'ok')}
    </div>
    <div class="tiles">
      ${tile('Total decisions', fmtInt(o.decisions))}${tile('Forecast-influenced decisions', fmtInt(o.forecastDecisions))}${tile('Peak EV charging', unit(f1(o.peakEV), 'kW'))}${tile('Peak controlled site demand', unit(f1(o.peakSite), 'kW'))}${tile('Grid-safe intervals', `${o.safeIntervals} / ${o.totalIntervals}`, 'ok')}
    </div>
    <div class="tiles">
      ${tile('Average completion', o.avgCompletion + '%')}${tile('Unmet energy', unit(o.unmet, 'kWh'), 'warn')}${tile('Deadline misses', o.deadlineMisses, 'warn')}
    </div>
    ${card('Optimization decision log', `<div id="dec-table"></div>`, { sub: 'Latest 15-minute optimization rounds. Select a row to see why that vehicle received that power.', cls: 'plain' })}
    <div class="grid">
      ${card('Why was this EV given this power?', `<div id="dec-why"></div>`, { cls: 'c7', sub: 'Explainable optimization' })}
      ${card('Optimization timeline', `<div class="tl">${GC.ALLOC_TIMELINE.map(a => `<div class="tl-i ${a.p >= 6 ? 'amber' : 'blue'}"><span class="t">${a.t}</span><span class="d"><i></i></span><p><b class="mono">${a.ev}</b> → ${f1(a.p)} kW<em>allocation ${a.p >= 6 ? 'raised' : 'trimmed'} by the look-ahead controller</em></p></div>`).join('')}</div>
        <div style="margin-top:8px"><div class="card-t" style="margin-bottom:8px">Dynamic charging allocation</div><div id="alloc-chart"></div></div>`, { cls: 'c5', sub: 'How charging allocations change over time.' })}
    </div>`;
  },
  mount() { Pages.optimization.table(); Pages.optimization.why(); const a = GC.allocSeries; const cols = [COLORS.grid, COLORS.building, COLORS.solar, COLORS.mint];
    Charts.line($('#alloc-chart'), { labels: a.t, unit: 'kW', height: 230, xTicks: 4, yMax: 8, aria: 'Allocation per EV over time', series: a.ids.map((id, k) => ({ key: id, label: id, color: cols[k], values: a.s[k], step: true, width: 2, noDot: true })) }); },
  table() {
    const rows = GC.DECISIONS.slice(0, 14);
    $('#dec-table').innerHTML = `<div class="tbl-wrap" style="max-height:440px"><table><thead><tr><th>Timestamp</th><th>EV ID</th><th>SOC</th><th>Required avg power</th><th>Slack hours</th><th>Forecast building demand</th><th>Forecast available capacity</th><th>Competing EV demand</th><th>Forecast congestion</th><th>Forecast feasibility</th><th>Forecast urgency</th><th>Priority score</th><th>Allocated power</th><th>Decision reason</th></tr></thead><tbody>
      ${rows.map(d => `<tr class="click ${d.i === S.opt.sel ? 'sel' : ''}" data-act="sel-dec" data-i="${d.i}"><td class="mono">${d.t}</td><td class="mono"><b>${d.ev}</b></td><td>${d.soc}%</td><td>${f1(d.reqAvg)} kW</td><td>${f1(d.slack)} h</td><td>${f1(d.fbBuilding)} kW</td><td>${f1(d.fbCap)} kW</td><td>${f1(d.comp)} kW</td><td>${lvl(d.congestion)}</td><td>${chip(d.feas, d.feas === 'Feasible' ? 'st-safe' : d.feas === 'Tight' ? 'st-warn' : 'st-crit', false)}</td><td>${d.urg.toFixed(2)}</td><td><b>${d.score.toFixed(2)}</b></td><td>${f1(d.alloc)} kW</td><td class="wrap">${d.reason}</td></tr>`).join('')}</tbody></table></div>`;
  },
  why() {
    const d = GC.DECISIONS[S.opt.sel];
    $('#dec-why').innerHTML = `
      <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div><div class="v v-lg mono" style="font-family:var(--f-mono)">${d.ev}</div><div class="tx3" style="font-size:12px;margin-top:4px">Decision recorded at ${d.t}</div></div>
        <div style="display:flex;gap:26px"><div><div class="k">Priority score</div><div class="v v-lg">${d.score.toFixed(2)}</div></div><div><div class="k">Allocated power</div><div class="v v-lg">${unit(f1(d.alloc), 'kW')}</div></div></div>
      </div>
      ${GC.FACTOR_KEYS.map(k => { const v = d.factors[k], on = Math.round(v * 10); return `<div class="factor"><span class="k">${GC.FACTOR_LABEL[k]}</span><span class="blocks" role="img" aria-label="${Math.round(v * 100)} percent">${Array.from({ length: 10 }, (_, i) => `<i class="${i < on ? 'on' : ''}"></i>`).join('')}</span><b>${v.toFixed(2)}</b></div>`; }).join('')}
      <div class="k" style="margin:16px 0 8px">Decision explanation</div>
      <div class="why">${d.reason}</div>
      <p class="tx3" style="margin-top:10px;font-size:12.5px">Generated from the recorded decision reason for this optimization round.</p>`;
  }
};

/* ============================ GRID & ENERGY ============================ */
Pages.grid = {
  title: 'Grid & Energy', sub: TAG,
  html() {
    const s = GC.snap(), ds = GC.stats, st = GC.status(), evU = GC.SERIES[GC.SERIES.length - 1].evU;
    const dist = [['Grid', ds.gridE, COLORS.grid], ['Solar', ds.solarE, COLORS.solar], ['Building', ds.bldE, COLORS.building], ['EV charging', ds.evE, COLORS.ev]], mx = Math.max(...dist.map(d => d[1]));
    const solarUtil = ds.solarUtil, share = ds.renewShare;
    return `
    <p class="lead-p">A detailed look at the energy ecosystem: what the site draws, what the sun supplies, and how Grid Charge keeps the difference under the grid limit.</p>
    <div class="tiles">
      ${tile('Grid limit', unit(GC.LIMIT, 'kW'), 'hl')}${tile('Building demand', unit(f1(s.building), 'kW'))}${tile('Solar generation', unit(f1(s.solar), 'kW'))}${tile('EV charging', unit(f1(s.ev), 'kW'))}${tile('Grid import', unit(f1(s.gridImport), 'kW'))}${tile('Available headroom', unit(f1(s.headroom), 'kW'), st.key === 'safe' ? 'ok' : 'warn')}
    </div>
    ${card('Grid safety', `
      <div class="tiles">
        ${tile('Controlled overload', unit(f1(ds.ctrlOverload), 'kW'), 'ok')}${tile('Uncontrolled overload', unit(f1(ds.uncOverload), 'kW'), 'bad')}${tile('Grid-safe intervals', `${ds.safeIntervals} / ${ds.totalIntervals}`)}${tile('Safety', ds.safety + '%', 'ok')}
        <div class="tile hl" style="display:flex;flex-direction:column;align-items:flex-start;justify-content:space-between;gap:10px"><span class="k">Primary status</span>${chip(st.key === 'safe' ? 'SAFE' : st.label, st.cls)}</div>
      </div>`, { cls: 'plain' })}
    ${card('Controlled vs uncontrolled charging', `
      <div class="split">
        <div class="eq"><div class="k" style="margin-bottom:4px">Without smart control</div>
          <div class="row"><span>Building demand</span><span class="num">${f1(s.building)} kW</span></div><div class="op">+</div>
          <div class="row"><span>Uncontrolled EV demand</span><span class="num">${f1(evU)} kW</span></div><div class="op">−</div>
          <div class="row"><span>Solar</span><span class="num">${f1(s.solar)} kW</span></div><div class="op">=</div>
          <div class="res bad">Potential grid overload <span style="font-family:var(--f-body);font-weight:600;font-size:.8em;display:block;margin-top:4px">${f1(s.building + evU - s.solar)} kW now · peaks at ${f1(ds.peakUnc)} kW, ${f1(ds.uncOverload)} kW over the ${GC.LIMIT} kW limit</span></div></div>
        <div class="eq"><div class="k" style="margin-bottom:4px;color:var(--mint)">With Grid Charge</div>
          <div class="row"><span>Building demand</span><span class="num">${f1(s.building)} kW</span></div><div class="op">+</div>
          <div class="row"><span>Optimized EV charging</span><span class="num">${f1(s.ev)} kW</span></div><div class="op">−</div>
          <div class="row"><span>Solar</span><span class="num">${f1(s.solar)} kW</span></div><div class="op">=</div>
          <div class="res good">Grid-safe site demand <span style="font-family:var(--f-body);font-weight:600;font-size:.8em;display:block;margin-top:4px">${f1(s.gridImport)} kW now · peaks at ${f1(ds.peakCtrl)} kW, always ≤ ${GC.LIMIT} kW</span></div></div>
      </div>
      <div style="margin-top:24px"><div id="cu-chart"></div></div>`, { sub: 'The clearest view of what intelligent charging control changes — over the last 24 hours.', cls: '' })}
    <div class="grid">
      ${card('Energy source distribution', `<div class="dist">${dist.map(d => `<div class="row"><span class="k" style="color:var(--lav-200)">${d[0]}</span><div class="bar" style="height:14px"><i style="width:${d[1] / mx * 100}%;background:${d[2]}"></i></div><b class="num">${fmtInt(d[1])} kWh</b></div>`).join('')}</div>
        <div class="stat-list" style="margin-top:18px"><div class="stat"><span class="k">Solar energy used</span><b>${fmtInt(ds.solarUsed)} kWh</b></div><div class="stat"><span class="k">Grid energy used</span><b>${fmtInt(ds.gridUsed)} kWh</b></div><div class="stat"><span class="k">Renewable contribution</span><b>${share}%</b></div></div>`, { cls: 'c6', sub: 'Last 24 hours' })}
      ${card('Solar / renewable utilization', `
        <div style="display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center"><div style="display:flex;gap:14px;flex-wrap:wrap">${Charts.ring(solarUtil, { size: 104, stroke: 11, color: COLORS.solar, aria: 'Solar utilization' })}${Charts.ring(share, { size: 104, stroke: 11, color: COLORS.grid, aria: 'Renewable share' })}</div>
        <div class="stat-list"><div class="stat"><span class="k">Solar available</span><b>${fmtInt(ds.solarE)} kWh</b></div><div class="stat"><span class="k">Solar used</span><b>${fmtInt(ds.solarUsed)} kWh</b></div><div class="stat"><span class="k">Solar utilization</span><b>${solarUtil}%</b></div><div class="stat"><span class="k">Renewable share</span><b>${share}%</b></div></div></div>
        <p class="tx2" style="margin-top:16px;font-size:13px">Grid Charge does not only manage grid capacity — it shifts charging into the hours when the sun is producing.</p>`, { cls: 'c6', sub: 'Last 24 hours' })}
    </div>`;
  },
  mount() {
    const p = GC.profile('24H');
    Charts.line($('#cu-chart'), {
      labels: p.map(x => x.t), unit: 'kW', height: 300, xTicks: 6, aria: 'Controlled versus uncontrolled site demand', overload: { key: 'unc', value: GC.LIMIT },
      series: [
        { key: 'unc', label: 'Uncontrolled Site Demand', color: COLORS.unc, values: p.map(x => x.unc), width: 2 },
        { key: 'grid', label: 'Controlled Site Demand', color: COLORS.mint, values: p.map(x => x.grid), area: true },
        { key: 'limit', label: 'Grid Limit', color: COLORS.limit, values: p.map(x => x.limit), dash: '6 6', width: 1.8 }
      ]
    });
  }
};

/* ============================ SITE ASSESSMENT ============================ */
const siteInputs = [
  ['grid', 'Grid capacity', 'kW', 'Grid Capacity', 1], ['building', 'Peak building demand', 'kW', 'Peak Building Demand', 0], ['solar', 'Solar capacity', 'kW', 'Solar Capacity', 0],
  ['evs', 'EVs per day', 'EVs', 'EVs Per Day', 1], ['energy', 'Average energy per EV', 'kWh', 'Average Energy Per EV', 1], ['hours', 'Average parking duration', 'hours', 'Average Parking Duration', 1]
];
Pages.site = {
  title: 'Site Assessment', sub: TAG,
  html() {
    const a = S.site;
    return `
    <p class="lead-p">Site Assessment is the infrastructure-planning layer. It answers one question: how much EV charging infrastructure should this location have?</p>
    <div class="grid">
      ${card('Site details', `
        <form id="site-form" novalidate>
          <div class="field" style="margin-bottom:18px"><span class="k" style="color:var(--lav-300)" id="site-type-l">Site type</span>
            <div class="types" role="group" aria-labelledby="site-type-l">${GC.SITE_TYPES.map(t => `<button type="button" class="type ${a.type === t.k ? 'on' : ''}" data-act="type" data-v="${t.k}" aria-pressed="${a.type === t.k}">${I(t.i)}${t.k}</button>`).join('')}</div></div>
          <div class="form-grid">${siteInputs.map(([k, l, u]) => `<div class="field"><label for="si-${k}">${l}</label><div class="inp-unit"><input id="si-${k}" class="inp num" type="number" inputmode="decimal" min="0" step="any" value="${a[k]}" data-bind="site.${k}"><span>${u}</span></div></div>`).join('')}</div>
          <div id="site-err" role="alert" style="margin-top:14px;color:var(--coral);font-weight:700;min-height:20px">${a.err || ''}</div>
          <div style="margin-top:6px;display:flex;gap:12px;flex-wrap:wrap;align-items:center"><button class="btn btn-cream" type="submit">Assess site ${I('arrow')}</button><span class="tx3" style="font-size:12.5px">Prefilled with an example ${a.type.toLowerCase()} — change any value and reassess.</span></div>
        </form>`, { cls: 'c5' })}
      <div class="c7" id="site-result" style="display:flex;flex-direction:column;gap:18px;min-width:0"></div>
    </div>`;
  },
  mount() { Pages.site.result(); $('#site-form').addEventListener('submit', e => { e.preventDefault(); Pages.site.submit(); }); },
  submit() {
    const a = S.site, need = ['grid', 'building', 'solar', 'evs', 'energy', 'hours'];
    const bad = need.find(k => !(Number(a[k]) >= 0) || a[k] === '' || (['grid', 'evs', 'energy', 'hours'].includes(k) && !(Number(a[k]) > 0)));
    if (bad) { a.err = `Enter a ${['grid', 'evs', 'energy', 'hours'].includes(bad) ? 'number above 0' : 'number (0 or more)'} for “${siteInputs.find(x => x[0] === bad)[1]}”.`; $('#site-err').textContent = a.err; $('#si-' + bad).focus(); return; }
    a.err = ''; $('#site-err').textContent = ''; a.done = true; Pages.site.result(true);
  },
  result(flash) {
    const a = S.site, n = { grid: +a.grid, building: +a.building, solar: +a.solar, evs: +a.evs, energy: +a.energy, hours: +a.hours }, r = GC.assess(n);
    const bPct = Math.min(100, n.building / n.grid * 100), cPct = Math.min(100 - bPct, r.capacity / n.grid * 100), rest = Math.max(0, 100 - bPct - cPct);
    const stCls = r.stress === 'LOW' ? 'st-safe' : r.stress === 'MODERATE' ? 'st-warn' : 'st-crit', sCls = r.solarUtil === 'HIGH' ? 'st-safe' : r.solarUtil === 'MEDIUM' ? 'st-warn' : 'st-lav';
    const paras = [];
    if (r.budget <= 0) paras.push(`The peak building demand (${fmtInt(n.building)} kW) already uses almost all of the ${fmtInt(n.grid)} kW grid capacity. This site should upgrade its connection before adding chargers.`);
    else paras.push(`The site has ${r.simult >= r.chargers ? 'sufficient' : 'enough'} grid capacity for the recommended ${f1(r.capacity)} kW of charging infrastructure when intelligent load balancing is used${r.simult < r.chargers ? `. Only ${r.simult} of the ${r.chargers} chargers can deliver full power at the same time` : ''}.`);
    paras.push(n.solar > 0 ? `Solar availability (${fmtInt(n.solar)} kW) reduces net grid demand and improves renewable utilization — it can cover about ${Math.round(Math.min(1, r.cover) * 100)}% of the charging capacity at midday.` : 'With no solar on site, charging draws entirely from the grid; adding solar would reduce net demand and improve renewable utilization.');
    paras.push(`Simultaneous charging should be managed to avoid excessive peak demand: at full use the site reaches ${Math.round(r.stressRatio * 100)}% of its grid capacity.`);
    $('#site-result').innerHTML = `
      ${card('Recommended charging infrastructure', `
        <div class="reco">
          ${tile('Recommended chargers', r.chargers, 'hl')}${tile('Maximum simultaneous charging', r.simult)}${tile('Recommended charging capacity', unit(f1(r.capacity), 'kW'))}
          <div class="tile"><span class="k">Grid stress</span><span style="margin-top:10px;display:block">${chip(r.stress, stCls)}</span></div>
          <div class="tile"><span class="k">Solar utilization</span><span style="margin-top:10px;display:block">${chip(r.solarUtil, sCls)}</span></div>
          <div class="tile"><span class="k">Recommended strategy</span><span class="v v-md" style="font-size:1rem;margin-top:8px;display:block;line-height:1.25">${r.strategy}</span></div>
        </div>
        <div style="margin-top:22px"><div class="k" style="margin-bottom:10px">Peak-hour grid budget · ${fmtInt(n.grid)} kW connection</div>
          <div style="display:flex;height:20px;border-radius:99px;overflow:hidden;background:rgba(255,255,255,.1)"><i style="width:${bPct}%;background:${COLORS.building}"></i><i style="width:${cPct}%;background:${COLORS.grid}"></i><i style="width:${rest}%;background:repeating-linear-gradient(135deg,rgba(47,179,124,.5) 0 6px,rgba(47,179,124,.2) 6px 12px)"></i></div>
          <div class="chips" style="margin-top:12px;font-size:12.5px"><span><span style="color:${COLORS.building}">●</span> Building peak ${fmtInt(n.building)} kW</span><span><span style="color:${COLORS.grid}">●</span> EV capacity ${f1(r.capacity)} kW</span><span><span style="color:var(--mint)">●</span> Spare ${f1(Math.max(0, n.grid - n.building - r.capacity))} kW</span><span class="tx3">~${f1(r.perEv)} kW per vehicle</span></div></div>`, { cls: flash ? 'flash' : '' })}
      ${card('Why this recommendation?', `<div style="display:grid;gap:12px">${paras.map(p => `<p class="why" style="font-size:.98rem">${p}</p>`).join('')}</div>`, {})}`;
    if (flash) $('#site-result').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
};

/* ============================ WHAT-IF SIMULATION ============================ */
const WI_PRESETS = {
  Baseline: { limit: 240, evs: 70, solar: 150, bld: 100, maxP: 7.2 },
  'Double the fleet': { limit: 240, evs: 120, solar: 150, bld: 100, maxP: 7.2 },
  'Heat-wave building load': { limit: 240, evs: 70, solar: 150, bld: 135, maxP: 7.2 },
  'Grid derate': { limit: 180, evs: 70, solar: 150, bld: 100, maxP: 7.2 },
  'Add solar': { limit: 240, evs: 70, solar: 300, bld: 100, maxP: 7.2 },
  'Fast chargers': { limit: 240, evs: 70, solar: 150, bld: 100, maxP: 11 }
};
Pages.whatif = {
  title: 'What-If Simulation', sub: TAG,
  html() {
    const w = S.wi, sl = (k, l, mn, mx, stp, u) => `<div class="slider"><div class="top"><label for="wi-${k}" class="k" style="color:var(--lav-300)">${l}</label><b id="wi-${k}-v">${w[k]} ${u}</b></div><input id="wi-${k}" type="range" min="${mn}" max="${mx}" step="${stp}" value="${w[k]}" data-bind="wi.${k}" style="--p:${(w[k] - mn) / (mx - mn) * 100}%"></div>`;
    return `
    <p class="lead-p">Change the site, run the day again. The simulator replays 24 hours of arrivals with and without Grid Charge, using the same 15-minute optimizer, so you can see what a larger fleet, a smaller grid connection or more solar would do.</p>
    <div class="grid">
      ${card('Scenario', `
        <div class="presets" style="margin-bottom:22px">${Object.keys(WI_PRESETS).map(p => `<button type="button" data-act="preset" data-v="${p}">${p}</button>`).join('')}</div>
        <div style="display:grid;gap:22px">
          ${sl('limit', 'Grid limit', 120, 500, 10, 'kW')}${sl('evs', 'Vehicles per day', 10, 120, 5, 'EVs')}${sl('solar', 'Solar capacity', 0, 300, 10, 'kW')}${sl('bld', 'Building demand', 60, 150, 5, '%')}
          <div class="slider"><div class="top"><span class="k" style="color:var(--lav-300)">Max charger power</span></div><div>${seg('maxP', ['3.7', '7.2', '11'], String(w.maxP))}<span class="tx3" style="margin-left:10px;font-size:12.5px">kW per vehicle</span></div></div>
        </div>`, { cls: 'c4' })}
      <div class="c8" style="display:flex;flex-direction:column;gap:18px;min-width:0" id="wi-out"></div>
    </div>`;
  },
  mount() { Pages.whatif.run(); },
  run() {
    const w = S.wi, r = GC.simulate(w), avoided = r.overloadU;
    const verdict = r.overloadC > 0 ? { l: 'ATTENTION REQUIRED', c: 'st-crit', m: 'Building demand alone exceeds the grid limit — charging cannot fix this.' } : r.unmet > 5 ? { l: 'GRID CONSTRAINED', c: 'st-warn', m: `Grid stays safe, but ${r.missed} vehicles leave short of target.` } : { l: 'SYSTEM SAFE', c: 'st-safe', m: 'Grid stays safe and every vehicle reaches its target.' };
    $('#wi-out').innerHTML = `
      ${card('Result', `
        <div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:18px">${chip(verdict.l, verdict.c)}<span class="tx2">${verdict.m}</span></div>
        <div class="tiles">
          ${tile('Peak without control', unit(f1(r.peakU), 'kW'), r.peakU > w.limit ? 'bad' : '')}${tile('Peak with Grid Charge', unit(f1(r.peakC), 'kW'), r.peakC > w.limit ? 'bad' : 'ok')}${tile('Overload avoided', unit(f1(avoided), 'kW'), avoided > 0 ? 'hl' : '')}
          ${tile('Grid-safe intervals', `${r.safeC} / ${r.steps}`, r.safeC === r.steps ? 'ok' : 'warn', `<span class="tx3" style="font-size:12px">${r.safeU} / ${r.steps} without control</span>`)}
          ${tile('Unmet energy', unit(f1(r.unmet), 'kWh'), r.unmet > 5 ? 'warn' : 'ok', `<span class="tx3" style="font-size:12px">${r.missed} deadline misses</span>`)}${tile('Solar utilization', r.solarUtil + '%')}
        </div>`, { cls: '' })}
      ${card('Site demand over 24 hours', `<div id="wi-chart"></div>`, { sub: `Fleet demand ${fmtInt(r.demand)} kWh · ${w.evs} vehicles · ${w.limit} kW grid limit` })}`;
    Charts.line($('#wi-chart'), {
      labels: r.t, unit: 'kW', height: 300, xTicks: 6, aria: 'Simulated site demand', overload: { key: 'unc', value: w.limit },
      series: [
        { key: 'unc', label: 'Without Grid Charge', color: COLORS.unc, values: r.unc, width: 2, noDot: true },
        { key: 'ctl', label: 'With Grid Charge', color: COLORS.mint, values: r.ctl, area: true, noDot: true },
        { key: 'sol', label: 'Solar', color: COLORS.solar, values: r.sol, width: 1.6, noDot: true },
        { key: 'lim', label: 'Grid Limit', color: COLORS.limit, values: r.limit, dash: '6 6', width: 1.8 }
      ]
    });
  }
};

/* ============================ SYSTEM INFORMATION ============================ */
Pages.system = {
  title: 'System Information', sub: TAG,
  html() {
    const s = GC.snap(), st = GC.status(), sc = GC.getScenario();
    const rows = [['Forecast model', 'Building & solar demand, 6 h ahead', 'safe', 'Healthy'], ['Optimization engine', 'Look-ahead V5 · 15-minute rounds', 'safe', 'Healthy'], ['Smart controller', 'Charger set-points acknowledged', 'safe', 'Healthy'], ['Telemetry feed', 'Meters, chargers, inverter · 5 s poll', 'safe', 'Live'], ['Explainability log', `${fmtInt(GC.OPT.decisions)} decisions stored`, 'safe', 'Healthy']];
    return `
    <p class="lead-p">How Grid Charge is wired, what it is configured to protect, and how the system status you see in the top bar is worked out.</p>
    ${card('Architecture', `<div class="arch">
      <div class="a">${I('brain', 22)}<b>ML Predicts</b><p>Forecasts building demand, solar output and arrivals for the next six hours.</p></div>
      <div class="a">${I('sliders', 22)}<b>Optimization Decides</b><p>Scores every EV and allocates power within the grid limit each 15 minutes.</p></div>
      <div class="a">${I('bolt', 22)}<b>Controller Acts</b><p>Sends set-points to chargers and re-checks the constraint continuously.</p></div>
      <div class="a">${I('eye', 22)}<b>Dashboard Explains</b><p>Shows what was decided and why, in plain language.</p></div></div>`, { cls: 'plain' })}
    <div class="grid">
      ${card('Core safety constraint', `
        <div class="why" style="text-align:center;font-weight:700">Building Demand + EV Charging − Solar Generation ≤ Grid Limit</div>
        <div class="eq" style="margin-top:16px"><div class="row"><span>${f1(s.building)} + ${f1(s.ev)} − ${f1(s.solar)}</span><span class="num"><b>${f1(s.building + s.ev - s.solar)} kW</b></span></div>
        <div class="res ${s.violations ? 'bad' : 'good'}">${f1(s.gridImport)} kW ≤ ${GC.LIMIT} kW · ${s.violations ? 'limit at risk' : 'constraint satisfied'}</div></div>`, { cls: 'c6', sub: 'Evaluated live against the latest telemetry.' })}
      ${card('Configuration', `<div class="stat-list">
        <div class="stat"><span class="k">Site</span><b>${GC.SITE.name}</b></div><div class="stat"><span class="k">Site type</span><b>${GC.SITE.kind}</b></div>
        <div class="stat"><span class="k">Grid limit</span><b>${GC.LIMIT} kW</b></div><div class="stat"><span class="k">Transformer</span><b>${GC.SITE.transformer}</b></div>
        <div class="stat"><span class="k">Strategy</span><b>Look-ahead V5</b></div><div class="stat"><span class="k">Planning horizon / interval</span><b>6 hours / 15 minutes</b></div>
        <div class="stat"><span class="k">Data source</span><b>Simulated backend (demo)</b></div></div>`, { cls: 'c6' })}
      ${card('System health', `<div class="stat-list">${rows.map(r => `<div class="stat"><div><b>${r[0]}</b><div class="tx3" style="font-size:12.5px">${r[1]}</div></div>${chip(r[3], 'st-' + r[2])}</div>`).join('')}</div>`, { cls: 'c6' })}
      ${card('How status is decided', `
        <div class="stat-list">
          <div class="stat"><div>${chip('SYSTEM SAFE', 'st-safe')}</div><span class="tx2" style="font-size:13px">Grid utilization below 70%</span></div>
          <div class="stat"><div>${chip('GRID CONSTRAINED', 'st-warn')}</div><span class="tx2" style="font-size:13px">70% – 90%</span></div>
          <div class="stat"><div>${chip('ATTENTION REQUIRED', 'st-crit')}</div><span class="tx2" style="font-size:13px">Above 90%, or any limit violation</span></div></div>
        <div style="margin-top:18px"><div class="k" style="margin-bottom:8px">Demo · simulate a grid condition</div>
          <div class="seg" role="group" aria-label="Simulate grid condition">${[['normal', 'Normal'], ['constrained', 'Constrained'], ['attention', 'Attention']].map(([k, l]) => `<button type="button" data-act="scenario" data-v="${k}" class="${sc === k ? 'on' : ''}" aria-pressed="${sc === k}">${l}</button>`).join('')}</div>
          <p class="tx3" style="font-size:12.5px;margin-top:10px">Currently ${st.label} at ${s.util}% utilization. Watch the top bar and Command Center react.</p></div>`, { cls: 'c6' })}
    </div>`;
  },
  mount() {}
};

/* ============================ ABOUT ============================ */
Pages.about = {
  title: 'About', sub: TAG,
  html() {
    const factors = ['Building electricity demand', 'Local grid capacity', 'Transformer / grid limitations', 'EV battery State of Charge', 'EV arrival time', 'EV departure time', 'Target SOC', 'Energy required', 'Maximum charging power', 'Number of connected EVs', 'Competing EV charging demand', 'Solar / renewable availability', 'Future building demand', 'Forecasted grid congestion'];
    return `
    <div class="grid">
      <section class="card cream c8"><div class="k">Product</div><h2 style="font-family:var(--f-display);font-weight:900;font-size:clamp(1.6rem,3vw,2.4rem);margin-top:8px;line-height:1.2">Grid Charge — Smart EV Charging &amp; Localized Grid Management</h2>
        <p style="margin-top:14px;font-size:1.08rem;font-style:italic;font-family:var(--f-display)">${TAG}</p>
        <p style="margin-top:14px;max-width:640px;line-height:1.7">Grid Charge intelligently coordinates EV charging with building demand, renewable energy, and local grid capacity to reduce peak stress, improve renewable utilization, and ensure safe and explainable charging decisions.</p></section>
      ${card('In four words', `<div class="v v-lg" style="font-family:var(--f-display);line-height:1.5">Predict.<br>Optimize.<br>Balance.<br>Charge.</div>`, { cls: 'c4' })}
      ${card('Operational intelligence', `<p class="v v-md" style="font-family:var(--f-display);font-weight:700;line-height:1.5">“How should we charge the connected EVs right now?”</p><p class="tx2" style="margin-top:12px;line-height:1.65">Layer 2 — real-time and simulated operations. Individual vehicles are coordinated against current and forecasted energy conditions on the Command Center, EV Fleet, Charging Sessions and Optimization pages.</p>`, { cls: 'c6' })}
      ${card('Infrastructure planning', `<p class="v v-md" style="font-family:var(--f-display);font-weight:700;line-height:1.5">“How much EV charging infrastructure can this location safely support?”</p><p class="tx2" style="margin-top:12px;line-height:1.65">Layer 1 — site planning. Charger capacity, charger count, simultaneous charging capability, grid stress and renewable utilization, on the Site Assessment and What-If pages.</p>`, { cls: 'c6' })}
      ${card('What Grid Charge weighs at every decision', `<div class="chips">${factors.map(f => `<span class="chip st-lav" style="text-transform:none;letter-spacing:.02em;font-size:12.5px;font-weight:700">${f}</span>`).join('')}</div>`, { cls: 'c12' })}
      ${card('Website flow', `<div class="flow-map">${['Landing page', 'Get started', 'Command center'].map((n, i) => `<span class="n ${i === 2 ? 'hi' : ''}">${n}</span>${I('arrow')}`).join('')}<span class="n">EV Fleet</span><span class="tx3">·</span><span class="n">Charging Sessions</span><span class="tx3">·</span><span class="n">Optimization</span>${I('arrow')}<span class="n">Grid &amp; Energy</span>${I('arrow')}<span class="n">Site Assessment</span>${I('arrow')}<span class="n">What-If Simulation</span>${I('arrow')}<span class="n">System Information</span></div>`, { cls: 'c12 plain' })}
    </div>`;
  },
  mount() {}
};
