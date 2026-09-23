/* =====================================================================
   GRID CHARGE — simulated backend
   Everything the UI shows is served from here (never hard-coded in views):
   fleet, sessions, decision log, time-series, forecast, status logic,
   the what-if simulator and the site-assessment model.
   ===================================================================== */
const GC = (() => {
  const mulberry = seed => () => {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const r1 = x => Math.round(x * 10) / 10;
  const r2 = x => Math.round(x * 100) / 100;
  const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  const T = m => { m = ((Math.round(m) % 1440) + 1440) % 1440; return String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };
  const P = s => { const [h, m] = s.split(':').map(Number); return h * 60 + m; };

  const NOW = 14 * 60 + 15;          // simulated "current" time 14:15
  const LIMIT = 350;                 // site grid limit (kW)
  const SITE = { name: 'Meridian Commons', kind: 'Mixed-Use Site', limit: LIMIT, transformer: '400 kVA' };

  /* ---------------- live snapshot (+ demo override for status logic) ---------------- */
  const BASE = { building: 126.2, solar: 128.4, ev: 184.6, gridImport: 182.4 };
  let scenario = 'normal';
  const setScenario = s => { scenario = s; };
  const getScenario = () => scenario;
  function snap() {
    const s = { ...BASE, limit: LIMIT, violations: 0 };
    if (scenario === 'constrained') s.gridImport = 296.4;
    if (scenario === 'attention') { s.gridImport = 341.8; s.violations = 2; }
    s.headroom = r1(LIMIT - s.gridImport);
    s.util = r1((s.gridImport / LIMIT) * 100);
    return s;
  }
  function status() {
    const s = snap();
    if (s.violations > 0 || s.util >= 90) return { key: 'attention', label: 'ATTENTION REQUIRED', cls: 'st-crit', tone: 'crit', msg: 'Grid limit at risk — review controller allocations' };
    if (s.util >= 70) return { key: 'constrained', label: 'GRID CONSTRAINED', cls: 'st-warn', tone: 'warn', msg: 'Approaching capacity — controller is limiting EV allocations' };
    return { key: 'safe', label: 'SYSTEM SAFE', cls: 'st-safe', tone: 'safe', msg: 'Operating within safe capacity' };
  }

  /* ---------------- 24h energy profile (5-minute resolution) ---------------- */
  const bump = (h, c, w) => Math.exp(-Math.pow((h - c) / w, 2));
  const solarF = h => Math.max(0, Math.cos((h - 12.5) * Math.PI / 12.6)) * 152 * (1 - .05 * Math.abs(Math.sin(h * 3.3)));
  const bldF = h => 76 + 60 * bump(h, 13.5, 4.2) + 64 * bump(h, 19.5, 2) + 3 * Math.sin(h * 7.3) + 4 * Math.sin(h * 2.9 + 1);
  const evF = h => {
    const up = 1 / (1 + Math.exp(-(h - 7.6) * 2.2)), dn = 1 / (1 + Math.exp((h - 17.2) * 1.5));
    return 20 + 168 * up * dn + 96 * bump(h, 19.6, 2.1) + 5 * Math.sin(h * 5.1);
  };
  const ufF = h => 1.25 + .7 * bump(h, 8.7, 1.1) + .75 * bump(h, 19.1, 1.6);
  const nowH = NOW / 60;
  const offB = BASE.building - bldF(nowH), offE = BASE.ev - evF(nowH), offS = BASE.solar - solarF(nowH);
  const SERIES = (() => {
    const out = [];
    for (let i = 287; i >= 0; i--) {
      const m = NOW - i * 5, h = ((m / 60) % 24 + 24) % 24, d = i / 12;
      const building = Math.max(30, bldF(h) + offB * Math.exp(-d / 2.5));
      const ev = Math.max(0, evF(h) + offE * Math.exp(-d / 2.5));
      const solar = Math.max(0, solarF(h) + (solarF(h) > 1 ? offS * Math.exp(-d / 1.5) : 0));
      const grid = Math.max(0, building + ev - solar);
      const unc = Math.max(0, building + ev * ufF(h) - solar);
      out.push({ t: T(m), building: r1(building), ev: r1(ev), solar: r1(solar), grid: r1(grid), unc: r1(unc), evU: r1(ev * ufF(h)), limit: LIMIT });
    }
    const last = out[out.length - 1];
    Object.assign(last, { building: BASE.building, ev: BASE.ev, solar: BASE.solar, grid: BASE.gridImport, t: T(NOW) });
    return out;
  })();
  const RANGE_N = { '1H': 12, '6H': 72, '12H': 144, '24H': 287 };
  const profile = range => SERIES.slice(-(RANGE_N[range] + 1));
  const sparkOf = (key, n = 24) => SERIES.slice(-n).map(p => p[key]);

  function dayStats() {
    const stepH = 5 / 60, N = SERIES.length;
    const sum = k => SERIES.reduce((a, p) => a + p[k], 0) * stepH;
    const gridE = sum('grid'), solarE = sum('solar'), bldE = sum('building'), evE = sum('ev');
    const peak = k => Math.max(...SERIES.map(p => p[k]));
    const solarUsed = Math.min(solarE, bldE + evE) * .94;
    const overU = SERIES.filter(p => p.unc > LIMIT), overC = SERIES.filter(p => p.grid > LIMIT);
    const safeIntervals = SERIES.filter((p, i) => i % 3 === 0 && p.grid <= LIMIT).length;
    const totalIntervals = SERIES.filter((p, i) => i % 3 === 0).length;
    return {
      gridE: r1(gridE), solarE: r1(solarE), bldE: r1(bldE), evE: r1(evE),
      solarUsed: r1(solarUsed), gridUsed: r1(gridE),
      renewShare: Math.round((solarUsed / (bldE + evE)) * 100),
      solarUtil: Math.round((solarUsed / solarE) * 100),
      peakEV: r1(peak('ev')), peakCtrl: r1(peak('grid')), peakUnc: r1(peak('unc')),
      ctrlOverload: overC.length ? r1(Math.max(...overC.map(p => p.grid - LIMIT))) : 0,
      uncOverload: overU.length ? r1(Math.max(...overU.map(p => p.unc - LIMIT))) : 0,
      safeIntervals, totalIntervals, safety: Math.round((safeIntervals / totalIntervals) * 100)
    };
  }

  /* ---------------- forecast monitor ---------------- */
  const FORECAST = [
    { h: 'NEXT 15 MINUTES', k: '15M', building: 178.4, capacity: 68.2, level: 'MEDIUM', ev: 171.2, solar: 121.6 },
    { h: 'NEXT HOUR', k: '1H', building: 168.0, capacity: 92.5, level: 'MEDIUM', ev: 164.0, solar: 104.2 },
    { h: 'NEXT 3 HOURS', k: '3H', building: 141.3, capacity: 150.4, level: 'LOW', ev: 122.5, solar: 38.7 },
    { h: 'NEXT 6 HOURS', k: '6H', building: 152.9, capacity: 118.6, level: 'LOW', ev: 96.4, solar: 0 }
  ];

  /* ---------------- fleet + sessions ---------------- */
  const PIN = {
    1: { soc: 33, target: 90, dep: '15:00', arr: '08:30', cap: 60 },
    2: { soc: 43, target: 80, dep: '16:15', arr: '08:45', cap: 52 },
    3: { soc: 53, target: 80, dep: '17:30', arr: '09:00', cap: 64 },
    4: { soc: 63, target: 80, dep: '18:45', arr: '09:30', cap: 75 },
    8: { soc: 46, target: 90, dep: '15:45', arr: '09:45', cap: 60 },
    21: { soc: 58, target: 85, dep: '17:15', arr: '10:15', cap: 64 },
    23: { soc: 41, target: 90, dep: '16:30', arr: '09:00', cap: 60, completion: 72, max: 7.2 },
    24: { soc: 85, target: 90, dep: '15:30', arr: '09:15', cap: 56, init: 28 }
  };
  const UNMET = [9.10, 8.03, 5.50];
  const CH = ['Charging'];

  function buildFleet(seed) {
    const r = mulberry(seed), pick = a => a[Math.floor(r() * a.length)];
    const pinned = new Set([1, 2, 3, 4, 8, 21, 23, 24, 50]);
    const pool = []; for (let i = 1; i <= 50; i++) if (!pinned.has(i)) pool.push(i);
    for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
    const status = {}; pool.slice(0, 18).forEach((id, k) => { status[id] = k < 10 ? 'Complete' : k < 16 ? 'Queued' : 'Paused'; });
    const completeIds = pool.slice(0, 10);
    const evs = [];
    for (let id = 1; id <= 50; id++) {
      const p = PIN[id] || {}, st = status[id] || 'Charging';
      const cap = p.cap || pick([40, 52, 56, 60, 64, 75, 82]);
      const target = p.target || pick([80, 80, 90, 90, 100]);
      let arr, dep;
      if (st === 'Queued') { arr = 13 * 60 + 45 + Math.floor(r() * 3) * 15; dep = 18 * 60 + Math.floor(r() * 9) * 15; }
      else if (st === 'Complete') { arr = 7 * 60 + Math.floor(r() * 12) * 15; dep = 15 * 60 + Math.floor(r() * 16) * 15; }
      else { arr = 7 * 60 + Math.floor(r() * 22) * 15; dep = NOW + 45 + Math.floor(r() * 21) * 15; }
      if (p.arr) arr = P(p.arr); if (p.dep) dep = P(p.dep);
      let init = p.init || Math.round(12 + r() * 26), soc;
      if (p.soc != null) soc = p.soc;
      else if (st === 'Complete') soc = target;
      else if (st === 'Queued') soc = init = Math.round(14 + r() * 26);
      else soc = Math.round(clamp(init + 14 + r() * 34, 25, target - 6));
      if (!p.init && st !== 'Queued' && st !== 'Complete') init = Math.min(init, soc - 8);
      const ev = {
        n: id, id: 'EV-' + String(id).padStart(3, '0'), status: st, cap, target, soc, init,
        arr, dep, max: p.max || (r() < .18 ? 11 : 7.2), power: 0, missed: false, unmet: 0
      };
      evs.push(ev);
    }
    // deadline-missed sessions (part of the "complete" bucket)
    completeIds.slice(0, 3).forEach((id, k) => {
      const ev = evs[id - 1]; ev.cap = Math.max(ev.cap, 60); ev.init = 14 + k * 4; ev.target = 90; ev.missed = true; ev.unmet = UNMET[k];
      ev.soc = ev.target - Math.round(UNMET[k] / ev.cap * 1000) / 10;
    });
    // charging power: pinned 5.8 kW, remainder normalised so the fleet sums to exactly 184.6 kW
    const charging = evs.filter(e => e.status === 'Charging');
    const fixed = charging.filter(e => [1, 2, 3, 4, 23].includes(e.n));
    fixed.forEach(e => e.power = 5.8);
    const free = charging.filter(e => !fixed.includes(e));
    let raw = free.map(() => 4.4 + r() * 2.4);
    const want = 184.6 - fixed.length * 5.8, k = want / raw.reduce((a, b) => a + b, 0);
    free.forEach((e, i) => e.power = r1(raw[i] * k));
    const diff = r1(want - free.reduce((a, e) => a + e.power, 0)); free[free.length - 1].power = r1(free[free.length - 1].power + diff);
    // derived fields
    evs.forEach(e => {
      e.required = r1((e.target - e.soc) / 100 * e.cap);
      e.sessionReq = r1((e.target - e.init) / 100 * e.cap);
      e.delivered = e.status === 'Queued' ? 0 : r1((e.soc - e.init) / 100 * e.cap);
      const span = Math.max(1, e.target - e.init);
      e.completion = e.n === 23 ? 72 : e.status === 'Queued' ? 0 : clamp(Math.round((e.soc - e.init) / span * 100), 0, 100);
      const hrs = (e.dep - NOW) / 60;
      e.urgency = e.status === 'Complete' ? 'Done' : hrs < 2 ? 'High' : hrs < 4 ? 'Medium' : 'Low';
      e.priority = e.status === 'Complete' ? '—' : e.urgency === 'High' ? 'High' : e.urgency === 'Medium' ? 'Medium' : 'Low';
      if (e.n === 8 || e.n === 23) e.priority = 'High';
      e.sessionId = 'S-' + (1000 + e.n);
      e.sessionStatus = e.status === 'Complete' ? (e.missed ? 'Deadline Missed' : 'Completed') : e.status;
    });
    // hit 974.9 kWh total delivered by solving EV-050's initial SOC
    const e50 = evs[49], others = evs.filter(e => e !== e50).reduce((a, e) => a + e.delivered, 0);
    const need = 974.9 - others, init50 = e50.soc - need / e50.cap * 100;
    if (!(init50 >= 4 && init50 <= e50.soc - 8)) return null;
    e50.init = init50; e50.sessionReq = r1((e50.target - e50.init) / 100 * e50.cap); e50.delivered = r1(need);
    e50.completion = clamp(Math.round((e50.soc - e50.init) / (e50.target - e50.init) * 100), 0, 100);
    return evs;
  }
  let FLEET = null;
  for (let s = 11; !FLEET && s < 3000; s++) FLEET = buildFleet(s);

  const by = id => FLEET.find(e => e.id === id);

  /* per-EV history: charging power + SOC over the session */
  const histCache = {};
  function history(ev) {
    if (histCache[ev.id]) return histCache[ev.id];
    if (ev.status === 'Queued') return (histCache[ev.id] = { t: [], p: [], soc: [] });
    const r = mulberry(ev.n * 7919), end = Math.min(NOW, ev.dep), t = [], raw = [];
    const k = Math.max(3, Math.floor((end - ev.arr) / 15) + 1);
    const active = ev.status === 'Complete' ? Math.max(3, Math.round(k * .62)) : k;
    for (let i = 0; i < k; i++) {
      t.push(ev.arr + i * 15);
      let v = i < active ? (ev.max * .55 + r() * ev.max * .4) * (i === 0 ? .6 : 1) : 0;
      if (i >= active - 2 && i < active && ev.status === 'Complete') v *= .5;
      raw.push(v);
    }
    const last = ev.status === 'Charging' ? ev.power : raw[k - 1];
    if (ev.status === 'Charging') raw[k - 1] = last;
    const tgt = ev.delivered / .25, rest = raw.reduce((a, b) => a + b, 0) - (ev.status === 'Charging' ? last : 0);
    const scale = ev.status === 'Charging' ? Math.max(.2, (tgt - last) / (rest || 1)) : tgt / (rest || 1);
    const p = raw.map((v, i) => r1(Math.min(ev.max, (ev.status === 'Charging' && i === k - 1) ? v : v * scale)));
    let e = 0; const soc = p.map(v => { e += v * .25; return r1(Math.min(100, ev.init + e / ev.cap * 100)); });
    soc[k - 1] = ev.soc; if (ev.status === 'Charging') p[k - 1] = ev.power;
    return (histCache[ev.id] = { t: t.map(T), p, soc });
  }

  /* ---------------- decision log ---------------- */
  const FACTOR_KEYS = ['soc', 'urgency', 'energy', 'slack', 'congestion'];
  const FACTOR_LABEL = { soc: 'SOC', urgency: 'Departure urgency', energy: 'Energy requirement', slack: 'Grid slack', congestion: 'Forecast congestion' };
  const PHRASE = { soc: 'low SOC', urgency: 'high urgency', energy: 'large energy requirement', slack: 'tight grid slack', congestion: 'increasing forecast congestion' };
  const reasonOf = f => {
    const top = [...FACTOR_KEYS].sort((a, b) => f[b] - f[a]).slice(0, 3).map(k => PHRASE[k]);
    const s = top.join(' + '); return s.charAt(0).toUpperCase() + s.slice(1);
  };
  const DECISIONS = (() => {
    const r = mulberry(4242), ch = FLEET.filter(e => e.status === 'Charging'), rows = [];
    for (let i = 0; i < 48; i++) {
      const m = NOW - i * 5 - (i % 3), ev = i === 0 ? by('EV-023') : ch[Math.floor(r() * ch.length)];
      const f = i === 0 ? { soc: .8, urgency: .9, energy: .7, slack: .6, congestion: .8 }
        : { soc: r2(.25 + r() * .7), urgency: r2(.2 + r() * .78), energy: r2(.2 + r() * .7), slack: r2(.15 + r() * .75), congestion: r2(.2 + r() * .72) };
      const fb = r1(140 + r() * 60), cap = r1(30 + r() * 150), comp = r1(120 + r() * 80);
      const score = i === 0 ? .91 : r2(.28 * f.soc + .27 * f.urgency + .15 * f.energy + .12 * f.slack + .18 * f.congestion + .04);
      const congestion = i === 0 ? 'MEDIUM' : cap < 55 ? 'HIGH' : cap < 105 ? 'MEDIUM' : 'LOW';
      const slack = r1((ev.dep - m) / 60 - ev.required / (ev.max * .8));
      rows.push({
        i, t: T(m), ev: ev.id, soc: ev.soc, reqAvg: r1(ev.required / Math.max(.5, (ev.dep - m) / 60)), slack: Math.max(0.2, slack),
        fbBuilding: i === 0 ? 178.4 : fb, fbCap: i === 0 ? 68.2 : cap, comp: r1(comp), congestion,
        feas: slack > 1.6 ? 'Feasible' : slack > .7 ? 'Tight' : 'At risk', urg: r2(f.urgency), score,
        alloc: i === 0 ? 5.8 : r1(Math.min(ev.max, 3.4 + score * 3.6)), factors: f, reason: reasonOf(f)
      });
    }
    return rows;
  })();

  /* ---------------- backend V5 optimisation results ---------------- */
  const stats = dayStats();
  const OPT = {
    version: 'V5', strategy: 'LOOK-AHEAD', horizon: '6 HOURS', interval: '15 MINUTES', decisions: 1186,
    forecastDecisions: 742, avgCompletion: 98.3, unmet: 22.63, deadlineMisses: 3,
    peakEV: stats.peakEV, peakSite: stats.peakCtrl, safeIntervals: stats.safeIntervals, totalIntervals: stats.totalIntervals
  };
  const ALLOC_TIMELINE = [
    { t: '08:00', ev: 'EV-001', p: 5.8 }, { t: '08:15', ev: 'EV-001', p: 5.2 },
    { t: '08:30', ev: 'EV-003', p: 6.0 }, { t: '08:45', ev: 'EV-008', p: 4.2 }
  ];
  const allocSeries = (() => {
    const r = mulberry(99), ids = ['EV-001', 'EV-003', 'EV-008', 'EV-021'], out = { t: [], s: ids.map(() => []) };
    for (let m = P('08:00'); m <= NOW; m += 15) {
      out.t.push(T(m));
      ids.forEach((id, k) => {
        const prev = out.s[k].length ? out.s[k][out.s[k].length - 1] : 5.8;
        const dip = bump(m / 60, 12.5 + k * .6, 1.2) * 1.4;
        out.s[k].push(r1(clamp(prev + (r() - .5) * 1.1 - (dip * .1) + (5.8 - prev) * .12, 3.2, 7.2)));
      });
    }
    out.s[0][0] = 5.8; out.s[0][1] = 5.2; out.s[1][2] = 6.0; out.s[2][3] = 4.2; out.ids = ids;
    return out;
  })();

  const ACTIVITY = [
    { t: '14:15', tone: 'amber', a: 'EV-021 allocation adjusted', b: 'due to rising building demand.' },
    { t: '14:00', tone: 'amber', a: 'Solar availability increased.', b: 'Solar share of demand rose to 41%.' },
    { t: '13:45', tone: 'blue', a: 'EV-008 prioritized because', b: 'of approaching departure.' },
    { t: '13:30', tone: 'mint', a: 'Grid utilization increased.', b: 'Look-ahead controller adjusted EV allocations.' },
    { t: '13:15', tone: 'mint', a: 'EV-031 session completed', b: 'at target SOC 80%.' },
    { t: '13:00', tone: 'blue', a: '6 vehicles queued', b: 'while forecast congestion cleared.' }
  ];

  /* ---------------- fleet aggregates ---------------- */
  function fleetStats() {
    const c = { Charging: 0, Complete: 0, Queued: 0, Paused: 0 };
    FLEET.forEach(e => c[e.status]++);
    const avg = k => FLEET.reduce((a, e) => a + e[k], 0) / FLEET.length;
    return {
      total: FLEET.length, ...c, avgSoc: Math.round(avg('soc')), avgCompletion: Math.round(avg('completion')),
      required: r1(FLEET.reduce((a, e) => a + e.required, 0)), delivered: r1(FLEET.reduce((a, e) => a + e.delivered, 0)),
      power: r1(FLEET.reduce((a, e) => a + e.power, 0))
    };
  }
  function sessionStats() {
    const fs = fleetStats(), act = FLEET.filter(e => e.status === 'Charging');
    const dur = FLEET.filter(e => e.status !== 'Queued').map(e => (Math.min(NOW, e.dep) - e.arr) / 60);
    return {
      connected: fs.Charging, active: fs.Charging, completed: fs.Complete, queued: fs.Queued, paused: fs.Paused,
      missed: FLEET.filter(e => e.missed).length, energy: fs.delivered,
      avgDur: dur.reduce((a, b) => a + b, 0) / dur.length,
      avgPower: r1(act.reduce((a, e) => a + e.power, 0) / act.length),
      avgCompletion: Math.round(FLEET.filter(e => e.status !== 'Queued').reduce((a, e) => a + e.completion, 0) / FLEET.filter(e => e.status !== 'Queued').length)
    };
  }
  function sessionDetail(ev) {
    const r = mulberry(ev.n * 31), solarShare = ev.n === 24 ? .43 : r2(.3 + r() * .2);
    const remainingH = ev.status === 'Charging' ? ev.required / Math.max(ev.power, .1) : 0;
    const eta = ev.status === 'Charging' ? NOW + remainingH * 60 : null;
    const fin = ev.status === 'Complete' ? Math.min(ev.dep, ev.arr + Math.max(90, Math.round(ev.sessionReq / (ev.max * .7) * 60))) : null;
    return {
      solarShare, gridShare: r2(1 - solarShare), solarE: r1(ev.delivered * solarShare), gridE: r1(ev.delivered * (1 - solarShare)),
      remainingH, eta, fin,
      deadline: ev.status === 'Queued' ? 'Pending' : ev.status === 'Complete' ? (ev.missed ? 'Missed' : 'Met') : eta != null && eta > ev.dep ? 'At risk' : ev.status === 'Paused' ? 'At risk' : 'On track',
      adjustments: 4 + Math.floor(r() * 14)
    };
  }
  function optHistory(ev) {
    const h = history(ev), r = mulberry(ev.n * 17), rows = [];
    const n = Math.min(6, h.t.length);
    for (let k = 0; k < n; k++) {
      const idx = h.t.length - 1 - k, f = { soc: r2(.3 + r() * .6), urgency: r2(.3 + r() * .65), energy: r2(.3 + r() * .6), slack: r2(.2 + r() * .6), congestion: r2(.25 + r() * .65) };
      const cong = f.congestion > .7 ? 'HIGH' : f.congestion > .45 ? 'MEDIUM' : 'LOW';
      rows.push({ t: h.t[idx], p: h.p[idx], prio: r2(.28 * f.soc + .27 * f.urgency + .15 * f.energy + .12 * f.slack + .18 * f.congestion + .05), cond: `Congestion ${cong} · headroom ${r1(40 + r() * 140)} kW`, reason: reasonOf(f) });
    }
    return rows;
  }

  /* ---------------- what-if simulator (real, 15-min steps) ---------------- */
  function simulate(o) {
    const r = mulberry(2026), steps = 96, dt = .25, evs = [];
    for (let i = 0; i < o.evs; i++) {
      const arr = clamp(Math.round(38 + (r() + r() + r() - 1.5) * 12), 26, 62);
      const dwell = clamp(Math.round(30 + (r() - .5) * 20), 14, 46);
      evs.push({ arr, dep: Math.min(95, arr + dwell), need: 8 + r() * 30, max: o.maxP, left: 0 });
      evs[i].left = evs[i].need; evs[i].left2 = evs[i].need;
    }
    const bld = new Array(steps), sol = new Array(steps);
    for (let s = 0; s < steps; s++) { const h = s / 4; bld[s] = (76 + 60 * bump(h, 13.5, 4.2) + 64 * bump(h, 19.5, 2)) * o.bld / 100; sol[s] = Math.max(0, Math.cos((h - 12.5) * Math.PI / 12.6)) * o.solar * .93; }
    const unc = new Array(steps).fill(0), ctl = new Array(steps).fill(0), evU = new Array(steps).fill(0), evC = new Array(steps).fill(0);
    let solarUsedC = 0;
    for (let s = 0; s < steps; s++) {
      // uncontrolled: everyone charges flat-out on arrival
      let pu = 0; evs.forEach(e => { if (s >= e.arr && s < e.dep && e.left2 > 0) { const p = Math.min(e.max, e.left2 / dt); e.left2 -= p * dt; pu += p; } });
      evU[s] = pu; unc[s] = bld[s] + pu - sol[s];
      // controlled: allocate within headroom, most urgent (highest required average power) first
      const head = Math.max(0, o.limit - (bld[s] - sol[s]));
      const act = evs.filter(e => s >= e.arr && s < e.dep && e.left > 0).map(e => ({ e, req: Math.min(e.max, e.left / (Math.max(1, e.dep - s) * dt)) })).sort((a, b) => b.req / b.e.max - a.req / a.e.max);
      let used = 0;
      act.forEach(a => { const p = Math.min(a.req, head - used); if (p > 0) { a.p = p; used += p; } else a.p = 0; });
      act.forEach(a => { const extra = Math.min(a.e.max - a.p, head - used); if (extra > 0) { a.p += extra; used += extra; } });
      act.forEach(a => { a.act = Math.min(a.p, a.e.max, a.e.left / dt); a.e.left -= a.act * dt; });
      const pc = act.reduce((x, a) => x + a.act, 0);
      evC[s] = pc; ctl[s] = bld[s] + pc - sol[s]; solarUsedC += Math.min(sol[s], bld[s] + pc) * dt;
    }
    const clip = a => a.map(v => Math.max(0, v));
    const c = clip(ctl), u = clip(unc);
    const solarAvail = sol.reduce((a, v) => a + v * dt, 0);
    const unmet = evs.reduce((a, e) => a + Math.max(0, e.left), 0), missed = evs.filter(e => e.left > .5).length;
    const eps = .05, overU = u.filter(v => v > o.limit + eps).length, overC = c.filter(v => v > o.limit + eps).length;
    return {
      t: Array.from({ length: steps }, (_, s) => T(s * 15)), ctl: c.map(r1), unc: u.map(r1), bld: bld.map(r1), sol: sol.map(r1),
      limit: new Array(steps).fill(o.limit), evC: evC.map(r1), evU: evU.map(r1),
      peakC: r1(Math.max(...c)), peakU: r1(Math.max(...u)), overloadU: r1(Math.max(0, Math.max(...u) - o.limit)), overloadC: r1(Math.max(0, Math.max(...c) - o.limit - eps)),
      safeC: steps - overC, safeU: steps - overU, steps, unmet: r1(unmet), missed,
      demand: r1(evs.reduce((a, e) => a + e.need, 0)), solarUtil: solarAvail ? Math.round(solarUsedC / solarAvail * 100) : 0, solarAvail: r1(solarAvail)
    };
  }

  /* ---------------- site assessment model ---------------- */
  const SITE_TYPES = [
    { k: 'Residential Colony', i: 'home' }, { k: 'Apartment Community', i: 'apartment' }, { k: 'Office', i: 'briefcase' }, { k: 'Mall', i: 'bag' },
    { k: 'Commercial Building', i: 'commercial' }, { k: 'Campus', i: 'campus' }, { k: 'Hotel', i: 'hotel' }, { k: 'Mixed-Use Site', i: 'layers' }
  ];
  function assess(a) {
    const window = 14;                                       // hours per operating day
    const perEv = clamp(r1(a.energy / a.hours * 2), 3.7, 11); // kW per vehicle (2x the average need)
    const chargers = Math.max(1, Math.ceil(a.evs * a.hours / window));
    const budget = Math.max(0, a.grid * .9 - a.building + a.solar * .5);
    const simult = Math.max(0, Math.min(chargers, Math.floor(budget / perEv)));
    const capacity = r1(simult * perEv);
    const stressRatio = (a.building + capacity - a.solar * .5) / a.grid;
    const stress = stressRatio < .7 ? 'LOW' : stressRatio < .95 ? 'MODERATE' : 'HIGH';
    const cover = capacity ? a.solar / capacity : 0;
    const solarUtil = cover >= .6 ? 'HIGH' : cover >= .25 ? 'MEDIUM' : 'LOW';
    const strategy = stress === 'HIGH' ? 'PEAK SHAVING WITH LOOK-AHEAD' : simult < chargers ? 'SMART LOAD BALANCING' : solarUtil === 'HIGH' ? 'SOLAR-FIRST SCHEDULING' : 'STANDARD SCHEDULING';
    return { chargers, simult, capacity, perEv, stress, stressRatio, solarUtil, strategy, budget: r1(budget), cover };
  }

  return {
    NOW, LIMIT, SITE, T, P, r1, r2, clamp,
    snap, status, setScenario, getScenario,
    SERIES, profile, sparkOf, dayStats, stats, FORECAST,
    FLEET, by, history, fleetStats, sessionStats, sessionDetail, optHistory,
    DECISIONS, OPT, ALLOC_TIMELINE, allocSeries, FACTOR_KEYS, FACTOR_LABEL, ACTIVITY,
    simulate, SITE_TYPES, assess
  };
})();
