/**
 * SteelRoute AI — Frontend Application Logic
 * Interactive dashboard with Leaflet maps, Plotly charts, and API integration.
 */

// ===== State =====
let map = null;
let routeLine = null;
let originMarker = null;
let destMarker = null;
let portsData = { origins: [], destinations: [], all_ports: [] };

// ===== Plotly Dark Theme =====
const plotlyLayout = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, sans-serif', color: '#8892a8', size: 11 },
  margin: { l: 50, r: 20, t: 20, b: 40 },
  xaxis: {
    gridcolor: 'rgba(255,255,255,0.04)',
    linecolor: 'rgba(255,255,255,0.08)',
    tickfont: { size: 10 },
  },
  yaxis: {
    gridcolor: 'rgba(255,255,255,0.04)',
    linecolor: 'rgba(255,255,255,0.08)',
    tickfont: { size: 10 },
  },
  legend: { orientation: 'h', y: -0.15, font: { size: 10 } },
  hoverlabel: {
    bgcolor: '#0a1128',
    bordercolor: 'rgba(0,212,255,0.3)',
    font: { family: 'Inter', color: '#e8eaf0', size: 12 },
  },
};

const plotlyConfig = {
  displayModeBar: false,
  responsive: true,
};

// ===== Initialization =====

document.addEventListener('DOMContentLoaded', () => {
  initMap();
  loadPorts();
  setupForm();
});

// ===== Map =====

function initMap() {
  map = L.map('route-map', {
    center: [15, 80],
    zoom: 3,
    zoomControl: true,
    attributionControl: false,
  });

  // Dark tile layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 18,
  }).addTo(map);
}

function updateMap(originPort, destPort) {
  // Clear existing
  if (routeLine) map.removeLayer(routeLine);
  if (originMarker) map.removeLayer(originMarker);
  if (destMarker) map.removeLayer(destMarker);

  const originLatLng = [originPort.lat, originPort.lon];
  const destLatLng = [destPort.lat, destPort.lon];

  // Create curved route line
  const latlngs = generateCurve(originLatLng, destLatLng, 50);

  routeLine = L.polyline(latlngs, {
    color: '#00d4ff',
    weight: 2.5,
    opacity: 0.7,
    dashArray: '8, 6',
    className: 'route-line',
  }).addTo(map);

  // Origin marker (blue)
  originMarker = L.circleMarker(originLatLng, {
    radius: 8,
    fillColor: '#00d4ff',
    fillOpacity: 0.9,
    color: '#fff',
    weight: 2,
  }).addTo(map).bindPopup(
    `<b>📤 Origin</b><br>${originPort.port_name}, ${originPort.country}`
  );

  // Destination marker (green)
  destMarker = L.circleMarker(destLatLng, {
    radius: 8,
    fillColor: '#22c55e',
    fillOpacity: 0.9,
    color: '#fff',
    weight: 2,
  }).addTo(map).bindPopup(
    `<b>📥 Destination</b><br>${destPort.port_name}, ${destPort.country}`
  );

  // Fit bounds
  const bounds = L.latLngBounds([originLatLng, destLatLng]);
  map.fitBounds(bounds, { padding: [40, 40] });
}

function generateCurve(start, end, numPoints) {
  // Generate a great-circle-like curve between two points
  const points = [];
  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const lat = start[0] + (end[0] - start[0]) * t;
    const lon = start[1] + (end[1] - start[1]) * t;
    // Add curvature
    const curvature = Math.sin(t * Math.PI) * 8;
    points.push([lat + curvature, lon]);
  }
  return points;
}

// ===== Load Ports =====

async function loadPorts() {
  try {
    const res = await fetch('/api/ports');
    portsData = await res.json();

    const originSelect = document.getElementById('origin-select');
    const destSelect = document.getElementById('dest-select');

    originSelect.innerHTML = '<option value="">Select origin port</option>';
    portsData.origins.forEach(p => {
      originSelect.innerHTML += `<option value="${p.port_id}">${p.port_name}, ${p.country}</option>`;
    });

    destSelect.innerHTML = '<option value="">Select destination port</option>';
    portsData.destinations.forEach(p => {
      destSelect.innerHTML += `<option value="${p.port_id}">${p.port_name}, ${p.country}</option>`;
    });

    // Auto-select defaults
    originSelect.value = 'AUNEW';
    destSelect.value = 'INPRD';

    // Show default route on map
    updateMapFromSelectors();

  } catch (err) {
    console.error('Failed to load ports:', err);
  }
}

function updateMapFromSelectors() {
  const originId = document.getElementById('origin-select').value;
  const destId = document.getElementById('dest-select').value;

  if (!originId || !destId) return;

  const origin = portsData.all_ports.find(p => p.port_id === originId);
  const dest = portsData.all_ports.find(p => p.port_id === destId);

  if (origin && dest) {
    updateMap(origin, dest);
  }
}

// ===== Form Handling =====

function setupForm() {
  document.getElementById('optimize-form').addEventListener('submit', handleOptimize);
  document.getElementById('origin-select').addEventListener('change', updateMapFromSelectors);
  document.getElementById('dest-select').addEventListener('change', updateMapFromSelectors);
}

async function handleOptimize(e) {
  e.preventDefault();

  const btn = document.getElementById('optimize-btn');
  const btnText = document.getElementById('btn-text');
  const spinner = document.getElementById('btn-spinner');

  // UI: loading state
  btn.disabled = true;
  btnText.textContent = 'Analyzing...';
  spinner.style.display = 'block';

  const originId = document.getElementById('origin-select').value;
  const destId = document.getElementById('dest-select').value;
  const cargoMt = parseFloat(document.getElementById('cargo-input').value);
  const daysAhead = parseInt(document.getElementById('days-input').value);

  try {
    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin_id: originId,
        dest_id: destId,
        cargo_volume_mt: cargoMt,
        target_days_ahead: daysAhead,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Optimization failed');
    }

    const data = await res.json();
    renderResults(data);

  } catch (err) {
    alert('Error: ' + err.message);
    console.error(err);
  } finally {
    btn.disabled = false;
    btnText.textContent = '⚡ Analyze & Optimize';
    spinner.style.display = 'none';
  }
}

// ===== Render Results =====

function renderResults(data) {
  // Show results, hide placeholder
  document.getElementById('results-section').style.display = 'block';
  document.getElementById('results-placeholder').style.display = 'none';

  const recs = data.recommendations;
  if (!recs || recs.length === 0) {
    document.getElementById('results-section').innerHTML =
      '<div class="glass-card results-placeholder"><div class="placeholder-icon">⚠️</div><p class="placeholder-text">No feasible vessel found for this route and cargo volume.</p></div>';
    return;
  }

  const best = recs[0];

  // KPI Cards
  renderKPIs(best, data);

  // Freight Forecast Chart
  renderFreightChart(best);

  // Cost Donut
  renderCostDonut(best.cost_breakdown);

  // Market Chart (fuel + commodity)
  renderMarketChart(data);

  // Vessel Comparison Cards
  renderVesselCards(recs);

  // Timing Window
  renderTimingWindow(best);

  // Scroll to results
  document.getElementById('kpi-grid').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== KPI Cards =====

function renderKPIs(best, data) {
  // Total cost
  animateCounter('kpi-total-cost', best.cost_breakdown.total_cost, '$', '', true);
  document.getElementById('kpi-cost-per-mt').textContent =
    `$${best.cost_breakdown.cost_per_mt.toLocaleString()} per MT`;

  // Vessel
  document.getElementById('kpi-vessel').textContent = best.vessel_type;
  document.getElementById('kpi-vessel-sub').textContent =
    `${best.voyage.total_days} day voyage`;

  // Savings
  animateCounter('kpi-savings', best.potential_savings, '$', '', true);

  // Window
  document.getElementById('kpi-window').textContent =
    `Day ${best.best_window.start_day}–${best.best_window.end_day}`;
  document.getElementById('kpi-window-sub').textContent = 'optimal chartering window';
}

function animateCounter(elementId, target, prefix = '', suffix = '', abbrev = false) {
  const el = document.getElementById(elementId);
  const duration = 1200;
  const start = Date.now();
  const startVal = 0;

  function format(val) {
    if (abbrev && val >= 1000000) {
      return prefix + (val / 1000000).toFixed(1) + 'M' + suffix;
    }
    if (abbrev && val >= 1000) {
      return prefix + (val / 1000).toFixed(0) + 'K' + suffix;
    }
    return prefix + Math.round(val).toLocaleString() + suffix;
  }

  function tick() {
    const elapsed = Date.now() - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const current = startVal + (target - startVal) * eased;
    el.textContent = format(current);
    if (progress < 1) requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}

// ===== Freight Chart =====

function renderFreightChart(best) {
  const dates = best.freight_forecast_dates;
  const values = best.freight_forecast_values;
  const lower = best.freight_forecast_lower;
  const upper = best.freight_forecast_upper;

  // Confidence band (lower)
  const bandLower = {
    x: dates,
    y: lower,
    type: 'scatter',
    mode: 'lines',
    line: { width: 0 },
    showlegend: false,
    hoverinfo: 'skip',
  };

  // Confidence band (upper, fills to lower)
  const bandUpper = {
    x: dates,
    y: upper,
    type: 'scatter',
    mode: 'lines',
    line: { width: 0 },
    fill: 'tonexty',
    fillcolor: 'rgba(0, 212, 255, 0.08)',
    showlegend: false,
    hoverinfo: 'skip',
  };

  // Main line
  const mainLine = {
    x: dates,
    y: values,
    type: 'scatter',
    mode: 'lines',
    name: `${best.vessel_type} Freight Rate`,
    line: { color: '#00d4ff', width: 2.5 },
    hovertemplate: '%{x}<br>Rate: %{y:.0f}<extra></extra>',
  };

  // Best window highlight
  const ws = best.best_window.start_day - 1;
  const we = best.best_window.end_day - 1;
  const windowDates = dates.slice(ws, we + 1);
  const windowVals = values.slice(ws, we + 1);

  const windowLine = {
    x: windowDates,
    y: windowVals,
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Best Window',
    line: { color: '#22c55e', width: 3 },
    marker: { size: 6, color: '#22c55e' },
  };

  const layout = {
    ...plotlyLayout,
    yaxis: {
      ...plotlyLayout.yaxis,
      title: { text: 'BDI Index (Scaled)', font: { size: 10, color: '#5a6478' } },
    },
    shapes: [{
      type: 'rect',
      x0: windowDates[0],
      x1: windowDates[windowDates.length - 1],
      y0: 0,
      y1: 1,
      yref: 'paper',
      fillcolor: 'rgba(34,197,94,0.06)',
      line: { width: 0 },
    }],
  };

  Plotly.newPlot('freight-chart', [bandLower, bandUpper, mainLine, windowLine], layout, plotlyConfig);
}

// ===== Cost Donut =====

function renderCostDonut(breakdown) {
  const labels = Object.keys(breakdown.breakdown_pct);
  const values = Object.values(breakdown.breakdown_pct);
  const colors = ['#00d4ff', '#7c5cff', '#ffb84d', '#22c55e', '#ff5c5c', '#00e5c6'];

  const trace = {
    values: values,
    labels: labels,
    type: 'pie',
    hole: 0.65,
    marker: {
      colors: colors,
      line: { color: '#060b18', width: 2 },
    },
    textinfo: 'percent',
    textfont: { color: '#e8eaf0', size: 10, family: 'Inter' },
    hovertemplate: '%{label}<br>%{percent}<br>$%{value:.1f}%<extra></extra>',
    sort: false,
  };

  const layout = {
    ...plotlyLayout,
    margin: { l: 10, r: 10, t: 10, b: 10 },
    showlegend: true,
    legend: {
      orientation: 'v',
      y: 0.5,
      x: 1.05,
      font: { size: 9, color: '#8892a8' },
    },
    annotations: [{
      text: `<b>$${(breakdown.total_cost / 1000000).toFixed(1)}M</b>`,
      showarrow: false,
      font: { size: 16, color: '#e8eaf0', family: 'Inter' },
    }],
  };

  Plotly.newPlot('cost-donut', [trace], layout, plotlyConfig);
}

// ===== Market Chart =====

function renderMarketChart(data) {
  const fuelTrace = {
    x: data.fuel_forecast.dates,
    y: data.fuel_forecast.values,
    type: 'scatter',
    mode: 'lines',
    name: 'Bunker Fuel (VLSFO)',
    line: { color: '#ffb84d', width: 2 },
    yaxis: 'y',
  };

  const commodityTrace = {
    x: data.commodity_forecast.dates,
    y: data.commodity_forecast.values,
    type: 'scatter',
    mode: 'lines',
    name: 'Coking Coal FOB',
    line: { color: '#7c5cff', width: 2 },
    yaxis: 'y2',
  };

  const layout = {
    ...plotlyLayout,
    yaxis: {
      ...plotlyLayout.yaxis,
      title: { text: 'Fuel ($/MT)', font: { size: 10, color: '#ffb84d' } },
      side: 'left',
    },
    yaxis2: {
      ...plotlyLayout.yaxis,
      title: { text: 'Coal ($/MT)', font: { size: 10, color: '#7c5cff' } },
      side: 'right',
      overlaying: 'y',
      gridcolor: 'transparent',
    },
    legend: { ...plotlyLayout.legend, y: -0.2 },
  };

  Plotly.newPlot('market-chart', [fuelTrace, commodityTrace], layout, plotlyConfig);
}

// ===== Vessel Cards =====

function renderVesselCards(recs) {
  const grid = document.getElementById('vessel-grid');
  grid.innerHTML = '';

  const maxCost = Math.max(...recs.map(r => r.cost_breakdown.total_cost));

  recs.forEach((rec, idx) => {
    const card = document.createElement('div');
    card.className = `glass-card vessel-card animate-in${rec.is_recommended ? ' recommended' : ''}`;

    const cb = rec.cost_breakdown;
    const costPct = ((cb.total_cost / maxCost) * 100).toFixed(0);

    card.innerHTML = `
      <div class="vessel-name">${rec.vessel_type}</div>
      <div class="vessel-specs">
        DWT: ${(rec.voyage.cargo_mt / 1000).toFixed(0)}K MT · ${rec.voyage.total_days} days · ${rec.voyage.distance_nm} nm
      </div>
      <div class="cost-row">
        <span class="cost-label">Cargo FOB</span>
        <span>$${abbreviate(cb.cargo_fob_cost)}</span>
      </div>
      <div class="cost-row">
        <span class="cost-label">Freight</span>
        <span>$${abbreviate(cb.freight_cost)}</span>
      </div>
      <div class="cost-row">
        <span class="cost-label">Fuel</span>
        <span>$${abbreviate(cb.fuel_cost)}</span>
      </div>
      <div class="cost-row">
        <span class="cost-label">Vessel Hire</span>
        <span>$${abbreviate(cb.hire_cost)}</span>
      </div>
      <div class="cost-row">
        <span class="cost-label">Port + Insurance</span>
        <span>$${abbreviate(cb.port_charges + cb.insurance_cost)}</span>
      </div>
      <div class="cost-row">
        <span class="cost-label">Total Landed Cost</span>
        <span>$${abbreviate(cb.total_cost)}</span>
      </div>
      <div class="cost-bar-track">
        <div class="cost-bar-fill" style="width: 0%;"></div>
      </div>
      ${rec.potential_savings > 0 ? `
        <div class="timing-highlight" style="margin-top:12px;">
          <span class="timing-icon">💰</span>
          <div class="timing-text">
            <h4>Save $${abbreviate(rec.potential_savings)}</h4>
            <p>Charter on Day ${rec.best_window.start_day}–${rec.best_window.end_day}</p>
          </div>
        </div>
      ` : ''}
    `;

    grid.appendChild(card);

    // Animate cost bar
    setTimeout(() => {
      card.querySelector('.cost-bar-fill').style.width = costPct + '%';
    }, 100 + idx * 200);
  });
}

// ===== Timing Window =====

function renderTimingWindow(best) {
  const container = document.getElementById('timing-content');
  const w = best.best_window;

  container.innerHTML = `
    <div class="timing-highlight">
      <span class="timing-icon">📅</span>
      <div class="timing-text">
        <h4>Optimal Charter Window: Day ${w.start_day} to Day ${w.end_day}</h4>
        <p>
          Average rate in this window: <strong>${w.avg_rate.toFixed(0)}</strong> index points
          vs. period average: <strong>${best.avg_freight_rate.toFixed(0)}</strong>.
          Potential savings: <strong>$${abbreviate(best.potential_savings)}</strong>
          on total landed cost.
        </p>
      </div>
    </div>
    <div class="timing-highlight" style="margin-top: 12px; border-color: rgba(124,92,255,0.15); background: rgba(124,92,255,0.06);">
      <span class="timing-icon">🚢</span>
      <div class="timing-text">
        <h4>Voyage Summary: ${best.vessel_type}</h4>
        <p>
          Distance: ${best.voyage.distance_nm} nm ·
          Sea transit: ${best.voyage.sea_days} days ·
          Port time: ${(best.voyage.port_days_origin + best.voyage.port_days_dest).toFixed(1)} days ·
          Fuel consumption: ${best.voyage.fuel_consumed_mt} MT
        </p>
      </div>
    </div>
  `;
}

// ===== Utilities =====

function abbreviate(num) {
  if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
  return num.toFixed(0);
}
