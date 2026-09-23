/* Grid Charge live API client and GC compatibility bridge. */
const GridChargeAPI = (() => {
  const API_BASE = (window.GRID_CHARGE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '');

  async function request(path) {
    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, { headers: { Accept: 'application/json' } });
    } catch (error) {
      throw new Error(`Backend unavailable: ${error.message}`);
    }
    let body;
    try { body = await response.json(); } catch (_) { body = null; }
    if (!response.ok) {
      const detail = body && body.detail ? body.detail : `HTTP ${response.status}`;
      throw new Error(`${path}: ${detail}`);
    }
    return body;
  }

  return {
    base: API_BASE,
    health: () => request('/api/health'),
    dashboard: () => request('/api/dashboard'),
    evs: () => request('/api/evs'),
    ev: id => request(`/api/evs/${encodeURIComponent(id)}`),
    grid: () => request('/api/grid'),
    gridLatest: () => request('/api/grid/latest'),
    gridSummary: () => request('/api/grid/summary'),
    forecast: () => request('/api/forecast'),
    forecastSample: () => request('/api/forecast/sample'),
    optimization: () => request('/api/optimization'),
    optimizationDecisions: () => request('/api/optimization/decisions'),
    optimizationLatestDecisions: () => request('/api/optimization/decisions/latest'),
    optimizationEV: id => request(`/api/optimization/ev/${encodeURIComponent(id)}`)
  };
})();

const GridChargeLive = (() => {
  const num = (value, fallback = 0) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const bool = value => value === true || value === 1 || String(value).toLowerCase() === 'true';
  const iso = value => new Date(value);
  const minutes = value => { const date = iso(value); return Number.isNaN(date.getTime()) ? 0 : date.getUTCHours() * 60 + date.getUTCMinutes(); };
  const clock = value => { const date = iso(value); return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' }); };
  const escStatus = value => value === 'completed' ? 'Complete' : value === 'deadline_missed' ? 'Incomplete' : value === 'incomplete' ? 'Paused' : 'Queued';
  const priority = score => score >= .75 ? 'High' : score >= .5 ? 'Medium' : 'Low';
  const level = capacity => capacity < 50 ? 'HIGH' : capacity < 100 ? 'MEDIUM' : 'LOW';

  function buildSeries(grid) {
    return grid.slice().sort((a, b) => iso(a.timestamp) - iso(b.timestamp)).map(row => ({
      t: clock(row.timestamp), timestamp: row.timestamp,
      building: num(row.building_demand_kw), ev: num(row.optimized_ev_charging_kw),
      solar: num(row.solar_generation_kw), grid: num(row.controlled_site_demand_kw),
      unc: num(row.uncontrolled_site_demand_kw), evU: num(row.uncontrolled_requested_ev_power_kw),
      limit: num(row.grid_limit_kw), headroom: num(row.remaining_grid_capacity_kw)
    }));
  }

  function normalizeFleet(evs, decisions) {
    const latest = new Map();
    decisions.forEach(row => latest.set(row.ev_id, row));
    return evs.map((row, index) => {
      const decision = latest.get(row.ev_id) || {};
      const status = escStatus(row.charging_status);
      const arr = minutes(row.arrival_time), dep = minutes(row.departure_time);
      return {
        n: index + 1, id: row.ev_id, status, sessionStatus: bool(row.deadline_missed) ? 'Deadline Missed' : status === 'Complete' ? 'Completed' : status,
        sessionId: `S-${1000 + index + 1}`, cap: num(row.battery_capacity_kwh), target: num(row.target_soc),
        soc: num(row.current_soc), init: num(row.current_soc), arr, dep, max: num(row.max_charging_power_kw),
        power: num(row.optimized_charging_power_kw), required: num(row.energy_required_kwh),
        sessionReq: num(row.energy_required_kwh), delivered: num(row.energy_delivered_kwh),
        completion: num(row.completion_percentage), missed: bool(row.deadline_missed), unmet: num(row.energy_unmet_kwh),
        urgency: bool(row.deadline_missed) ? 'High' : num(row.completion_percentage) >= 100 ? 'Done' : 'Medium',
        priority: decision.priority_score == null ? '—' : priority(num(decision.priority_score)),
        dataSource: row.data_source || 'backend V5 artifact'
      };
    });
  }

  function normalizeForecast(rows) {
    const labels = [['15M', 'NEXT 15 MINUTES'], ['1H', 'NEXT HOUR'], ['3H', 'NEXT 3 HOURS'], ['6H', 'NEXT 6 HOURS']];
    const sorted = rows.slice().sort((a, b) => iso(a.timestamp) - iso(b.timestamp));
    return labels.map((entry, index) => {
      const row = sorted[Math.min(index, sorted.length - 1)] || {};
      return { k: entry[0], h: entry[1], building: num(row.predicted_building_demand_kw), capacity: num(row.forecast_available_capacity_kw), level: level(num(row.forecast_available_capacity_kw)), timestamp: row.timestamp };
    });
  }

  function normalizeDecisions(rows) {
    return rows.slice().sort((a, b) => iso(a.timestamp) - iso(b.timestamp)).map((row, index) => {
      const score = num(row.priority_score), congestion = num(row.forecast_congestion);
      return {
        i: index, t: clock(row.timestamp), timestamp: row.timestamp, ev: row.ev_id, soc: num(row.current_soc),
        reqAvg: num(row.required_average_power_kw), slack: num(row.slack_hours), fbBuilding: num(row.forecasted_building_demand_kw),
        fbCap: num(row.forecasted_available_ev_capacity_kw), comp: num(row.forecast_competing_ev_demand_kw),
        congestion: congestion > 1 ? 'HIGH' : congestion > .45 ? 'MEDIUM' : 'LOW', feas: num(row.forecast_feasibility_ratio) <= 1 ? 'Feasible' : 'At risk',
        urg: num(row.forecast_urgency_score), score, alloc: num(row.allocated_power_kw), reason: row.decision_reason || 'Recorded V5 decision',
        factors: { soc: Math.min(1, num(row.current_soc) / 100), urgency: num(row.forecast_urgency_score), energy: Math.min(1, num(row.required_average_power_kw) / 11), slack: Math.max(0, Math.min(1, 1 / (1 + num(row.slack_hours)))), congestion: Math.min(1, congestion) }
      };
    });
  }

  function apply(payload) {
    const grid = payload.grid.data || [], evs = payload.evs.data || [], forecast = payload.forecast.data || [];
    const decisions = payload.decisions.data || [], summary = payload.optimization, series = buildSeries(grid);
    const fleet = normalizeFleet(evs, decisions), normalizedDecisions = normalizeDecisions(decisions);
    const allocationRows = normalizedDecisions.slice(-24);
    const allocationIds = [...new Set(allocationRows.map(row => row.ev))].slice(0, 4);
    const latest = grid[grid.length - 1] || {}, stats = {
      gridE: Number((series.reduce((sum, row) => sum + row.grid, 0) * .25).toFixed(1)),
      solarE: Number((series.reduce((sum, row) => sum + row.solar, 0) * .25).toFixed(1)),
      bldE: Number((series.reduce((sum, row) => sum + row.building, 0) * .25).toFixed(1)),
      evE: Number((series.reduce((sum, row) => sum + row.ev, 0) * .25).toFixed(1)),
      solarUsed: Number((series.reduce((sum, row) => sum + row.solar, 0) * .25).toFixed(1)),
      gridUsed: Number((series.reduce((sum, row) => sum + row.grid, 0) * .25).toFixed(1)),
      renewShare: 0, solarUtil: 0, peakEV: num(summary.peak_ev_charging_kw), peakCtrl: num(summary.peak_controlled_site_demand_kw),
      peakUnc: Math.max(...series.map(row => row.unc), 0), ctrlOverload: num(summary.max_controlled_overload_kw), uncOverload: Math.max(...series.map(row => row.unc - row.limit), 0),
      safeIntervals: num(summary.grid_safe_intervals), totalIntervals: num(summary.total_intervals), safety: Math.round(num(summary.grid_safe_intervals) / Math.max(1, num(summary.total_intervals)) * 100)
    };
    const liveSnap = () => ({ building: num(latest.building_demand_kw), solar: num(latest.solar_generation_kw), ev: num(latest.optimized_ev_charging_kw), gridImport: num(latest.controlled_site_demand_kw), limit: num(latest.grid_limit_kw), violations: grid.filter(row => !row.grid_safe).length, headroom: num(latest.remaining_grid_capacity_kw), util: num(latest.grid_utilization_percent) });
    Object.assign(GC, {
      DATA_MODE: 'live', API_ERROR: '', LIMIT: num(latest.grid_limit_kw, 250),
      SITE: { name: 'V5 Residential Simulation', kind: 'Synthetic residential site', limit: num(latest.grid_limit_kw, 250), transformer: 'V5 grid limit' },
      NOW: minutes(latest.timestamp), FLEET: fleet, SERIES: series, FORECAST: normalizeForecast(forecast), stats,
      OPT: { version: 'V5', strategy: 'LOOK-AHEAD', horizon: '6 HOURS', interval: '15 MINUTES', decisions: decisions.length, forecastDecisions: decisions.filter(row => bool(row.forecast_influenced_decision)).length, avgCompletion: num(summary.average_completion_percent), unmet: num(summary.unmet_energy_kwh), deadlineMisses: num(summary.deadline_misses), peakEV: num(summary.peak_ev_charging_kw), peakSite: num(summary.peak_controlled_site_demand_kw), safeIntervals: num(summary.grid_safe_intervals), totalIntervals: num(summary.total_intervals) },
      DECISIONS: normalizedDecisions.slice(-48).map((row, index) => ({ ...row, i: index })),
      ALLOC_TIMELINE: normalizedDecisions.slice(-4).map(row => ({ t: row.t, ev: row.ev, p: row.alloc })),
      allocSeries: { t: allocationRows.map(row => row.t), ids: allocationIds, s: allocationIds.map(id => allocationRows.map(row => row.ev === id ? row.alloc : 0)) }
    });
    GC.snap = liveSnap;
    GC.status = () => { const snap = liveSnap(); if (snap.violations || snap.util >= 90) return { key: 'attention', label: 'ATTENTION REQUIRED', cls: 'st-crit', tone: 'crit', msg: 'Grid limit reached — V5 is protecting the site' }; if (snap.util >= 70) return { key: 'constrained', label: 'GRID CONSTRAINED', cls: 'st-warn', tone: 'warn', msg: 'V5 is limiting EV allocations' }; return { key: 'safe', label: 'SYSTEM SAFE', cls: 'st-safe', tone: 'safe', msg: 'Operating within safe capacity' }; };
    GC.fleetStats = () => { const counts = { Charging: 0, Complete: 0, Queued: 0, Paused: 0 }; fleet.forEach(row => { counts[row.status] = (counts[row.status] || 0) + 1; }); return { total: fleet.length, ...counts, avgSoc: Math.round(fleet.reduce((sum, row) => sum + row.soc, 0) / Math.max(1, fleet.length)), avgCompletion: Math.round(num(summary.average_completion_percent)), required: num(summary.required_energy_kwh), delivered: num(summary.delivered_energy_kwh), power: num(summary.peak_ev_charging_kw) }; };
    GC.sessionStats = () => { const fs = GC.fleetStats(); return { connected: latest.connected_ev_count || 0, active: fs.Charging, completed: fs.Complete, queued: fs.Queued, paused: fs.Paused, missed: num(summary.deadline_misses), energy: num(summary.delivered_energy_kwh), avgDur: 0, avgPower: fs.power / Math.max(1, fs.Charging), avgCompletion: fs.avgCompletion }; };
    GC.profile = range => { const counts = { '1H': 5, '6H': 25, '12H': 49, '24H': 97 }; return series.slice(-(counts[range] || 25)); };
    GC.sparkOf = (key, count = 24) => series.slice(-count).map(row => num(row[key]));
    GC.by = id => fleet.find(row => row.id === id);
    GC.history = ev => { const rows = decisions.filter(row => row.ev_id === ev.id); return { t: rows.map(row => clock(row.timestamp)), p: rows.map(row => num(row.allocated_power_kw)), soc: rows.map(row => num(row.current_soc)) }; };
    GC.optHistory = ev => decisions.filter(row => row.ev_id === ev.id).slice(-6).map(row => ({ t: clock(row.timestamp), p: num(row.allocated_power_kw), prio: num(row.priority_score), cond: `Forecast capacity ${num(row.forecasted_available_ev_capacity_kw)} kW`, reason: row.decision_reason || 'Recorded V5 decision' }));
    GC.sessionDetail = ev => ({ solarShare: 0, gridShare: 1, solarE: 0, gridE: ev.delivered, remainingH: 0, eta: null, fin: ev.status === 'Complete' ? ev.dep : null, deadline: ev.missed ? 'Missed' : ev.status === 'Complete' ? 'Met' : 'On track', adjustments: 0 });
    GC.DATA_PROVENANCE = payload.dashboard.provenance || {};
    window.dispatchEvent(new CustomEvent('gridcharge:data-ready'));
  }

  async function load() {
    const [dashboard, evs, grid, forecast, optimization, decisions] = await Promise.all([
      GridChargeAPI.dashboard(), GridChargeAPI.evs(), GridChargeAPI.grid(), GridChargeAPI.forecast(), GridChargeAPI.optimization(), GridChargeAPI.optimizationDecisions()
    ]);
    apply({ dashboard, evs, grid, forecast, optimization, decisions });
    return true;
  }

  return { load, apply };
})();

window.GridChargeAPI = GridChargeAPI;
window.GridChargeLive = GridChargeLive;
