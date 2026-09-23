/* =====================================================================
   GRID CHARGE — shell, router, events
   ===================================================================== */
const NAV = [
  ['command', 'Command Center', 'command'], ['fleet', 'EV Fleet', 'car'], ['sessions', 'Charging Sessions', 'plug'],
  ['optimization', 'Optimization', 'sliders'], ['grid', 'Grid & Energy', 'grid'], ['site', 'Site Assessment', 'pin'], ['whatif', 'What-If Simulation', 'flask']
];
const NAV2 = [['system', 'System Information', 'cog'], ['about', 'About', 'info']];
let current = null;

function buildShell() {
  const link = ([k, l, ic]) => `<a href="#/${k}" data-page="${k}">${I(ic)}<span>${l}</span></a>`;
  $('#app').innerHTML = `
    <aside class="side" id="side" aria-label="Main navigation">
      <a class="brand" href="#/" aria-label="Grid Charge home">${BRAND_MARK}<span class="brand-name">GRID CHARGE</span></a>
      <div class="sub">Charging Intelligence</div>
      <nav class="nav" aria-label="Application">${NAV.map(link).join('')}</nav>
      <div class="nav-sep"></div>
      <nav class="nav" aria-label="System">${NAV2.map(link).join('')}</nav>
      <div class="side-fill"></div>
      <div class="side-card" id="side-card"></div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="tb-l"><button class="tb-menu" type="button" data-act="menu" aria-label="Open navigation">${I('menu', 20)}</button>
          <div><h1 class="tb-title" id="tb-title"></h1><div class="tb-sub" id="tb-sub"></div></div></div>
        <div class="tb-r" id="tb-r"></div>
      </header>
      <main class="content" id="content"></main>
    </div>`;
}

function updateStatus() {
  const st = GC.status(), s = GC.snap();
  $('#tb-r').innerHTML = `<span class="tb-clock">${GC.SITE.name} · ${T(GC.NOW)}</span>
    <span class="chip ${st.cls}" role="status" aria-live="polite"><i class="dot"></i>${st.label}</span>
    <span class="chip st-lav">V5 look-ahead${current === 'command' ? ' optimization' : ''}</span>
    <span class="chip ${GC.DATA_MODE === 'live' ? 'st-safe' : 'st-warn'}">${GC.DATA_MODE === 'live' ? 'LIVE API' : 'DEMO DATA'}</span>`;
  $('#side-card').innerHTML = `<div class="row"><span class="l">Grid utilization</span><span class="v">${s.util}%</span></div><div class="mini-bar"><i style="width:${s.util}%"></i></div><div class="row" style="margin-top:10px"><span class="l">Headroom</span><span class="tx2" style="font-weight:700;font-size:12.5px">${f1(s.headroom)} kW</span></div>`;
}

function renderPage() {
  const pg = Pages[current];
  $('#tb-title').textContent = pg.title; $('#tb-sub').textContent = pg.sub;
  $$('.nav a').forEach(a => { const on = a.dataset.page === current; a.classList.toggle('on', on); on ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'); });
  $('#content').innerHTML = pg.html();
  updateStatus();
  pg.mount();
}

function route() {
  const key = location.hash.replace(/^#\/?/, '').split('/')[0];
  const wasApp = !$('#app').hidden;
  closeDrawer(); document.body.classList.remove('nav-open');
  if (Pages[key]) {
    current = key;
    if (!$('#app').innerHTML) buildShell();
    $('#landing').hidden = true; $('#app').hidden = false;
    document.title = pg(key).title + ' · Grid Charge';
    renderPage(); window.scrollTo(0, 0);
  } else {
    $('#app').hidden = true; $('#landing').hidden = false; document.title = 'Grid Charge';
    const target = key && document.getElementById(key);
    if (target) target.scrollIntoView(); else if (wasApp || !key) window.scrollTo(0, 0);
  }
}
const pg = k => Pages[k];

function closeDrawer() { const d = $('#drawer'); if (d.classList.contains('open')) { d.classList.remove('open'); d.innerHTML = ''; document.body.style.overflow = ''; } }

/* ---------- actions ---------- */
function setSeg(el) { $$('button', el.closest('.seg')).forEach(b => { const on = b === el; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); }); }
const Act = {
  menu() { document.body.classList.toggle('nav-open'); },
  seg(el) {
    const g = el.dataset.g, v = el.dataset.v; setSeg(el);
    if (g === 'range') { S.range = v; Pages.command.drawProfile(); }
    if (g === 'horizon') { S.horizon = v; Pages.command.drawForecast(); }
    if (g === 'sstatus') { S.sess.status = v; S.sess.page = 1; Pages.sessions.table(); }
    if (g === 'maxP') { S.wi.maxP = +v; Pages.whatif.run(); }
  },
  page(el) { const g = el.dataset.g; S[g === 'fleet' ? 'fleet' : 'sess'].page = +el.dataset.v; Pages[g === 'fleet' ? 'fleet' : 'sessions'].table(); },
  'open-ev'(el) { if (current === 'fleet') openEV(el.dataset.id); else { S.fleet.open = el.dataset.id; location.hash = '#/fleet'; } },
  'close-drawer': closeDrawer,
  'sel-session'(el) { S.sess.sel = el.dataset.id; Pages.sessions.table(); Pages.sessions.detail(); $('#sess-detail').scrollIntoView({ behavior: 'smooth', block: 'start' }); },
  'sel-dec'(el) { S.opt.sel = +el.dataset.i; Pages.optimization.table(); Pages.optimization.why(); $('#dec-why').closest('.card').scrollIntoView({ behavior: 'smooth', block: 'nearest' }); },
  scenario(el) { GC.setScenario(el.dataset.v); renderPage(); },
  type(el) { S.site.type = el.dataset.v; $$('.type').forEach(b => { const on = b === el; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); }); },
  preset(el) { S.wi = { ...WI_PRESETS[el.dataset.v] }; renderPage(); }
};
document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]'); if (!el) return;
  if (el.tagName === 'A') return;
  if (el.classList.contains('drawer-bg') && e.target !== el) return;
  Act[el.dataset.act] && Act[el.dataset.act](el, e);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { closeDrawer(); document.body.classList.remove('nav-open'); }
  if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('tr.click')) { e.preventDefault(); e.target.click(); }
});
let wiRaf = 0;
document.addEventListener('input', e => {
  const el = e.target.closest('[data-bind]'); if (!el) return;
  const [ns, k] = el.dataset.bind.split('.');
  if (ns === 'fleet') { S.fleet[k] = el.value; S.fleet.page = 1; Pages.fleet.table(); }
  else if (ns === 'sess') { S.sess.q = el.value; S.sess.page = 1; Pages.sessions.table(); }
  else if (ns === 'site') { S.site[k] = el.value; }
  else if (ns === 'wi') {
    S.wi[k] = +el.value;
    const u = { limit: 'kW', evs: 'EVs', solar: 'kW', bld: '%' }[k], mn = +el.min, mx = +el.max;
    $('#wi-' + k + '-v').textContent = el.value + ' ' + u; el.style.setProperty('--p', (el.value - mn) / (mx - mn) * 100 + '%');
    cancelAnimationFrame(wiRaf); wiRaf = requestAnimationFrame(() => Pages.whatif.run());
  }
});
document.addEventListener('click', e => { if (e.target.closest('.nav a')) document.body.classList.remove('nav-open'); });
// keyboard access for clickable table rows
new MutationObserver(() => $$('tr.click:not([tabindex])').forEach(r => r.setAttribute('tabindex', '0'))).observe(document.body, { childList: true, subtree: true });

/* ---------- boot ---------- */
$('#hero-art').innerHTML = heroArt();
const FEATS = [
  ['command', 'Command Center', 'command', 'The whole charging ecosystem at a glance: energy flow, grid status, forecast and fleet.'],
  ['fleet', 'EV Fleet', 'car', 'Battery, power, energy need and departure urgency for every connected vehicle.'],
  ['sessions', 'Charging Sessions', 'plug', 'What happened during each charging event, from arrival to departure.'],
  ['optimization', 'Optimization', 'sliders', 'Forecast-aware decisions with a plain-language reason for every kilowatt.'],
  ['grid', 'Grid & Energy', 'grid', 'Controlled versus uncontrolled demand, solar use and grid safety in one view.'],
  ['site', 'Site Assessment', 'pin', 'How many chargers can this location safely support? Get a sized recommendation.'],
  ['whatif', 'What-If Simulation', 'flask', 'Resize the fleet, the grid or the solar array and replay the day.']
];
$('#feat-grid').innerHTML = FEATS.map(f => `<a class="feat" href="#/${f[0]}"><span class="fi">${I(f[2])}</span><h3>${f[1]}</h3><p>${f[3]}</p></a>`).join('');
window.addEventListener('hashchange', route);
route();

/* Hydrate the existing GC contract from FastAPI without blocking the demo shell. */
if (window.GridChargeLive) {
  GridChargeLive.load().then(() => {
    if (current && Pages[current]) renderPage();
  }).catch(error => {
    GC.DATA_MODE = 'demo';
    GC.API_ERROR = error.message;
    if (current && Pages[current]) updateStatus();
    console.warn('Grid Charge backend unavailable; retaining demo data.', error);
  });
}
