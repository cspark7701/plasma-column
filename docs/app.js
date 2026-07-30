/* ==========================================================================
   Plasma Column Neutralizer Simulation - GitHub Pages Interactive Application
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initSimulator();
});

// 1. Navigation Tab Controller
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add('active');
        if (window.MathJax) {
          window.MathJax.typesetPromise([targetPanel]);
        }
      }
    });
  });
}

// 2. Physics Constants
const MP = 1.67262192e-27;
const QE = 1.602176634e-19;
const KB = 1.380649e-23;
const CLIGHT = 299792458.0;
const EPS0 = 8.8541878128e-12;

// 3. Interactive Neutralization Simulator
function initSimulator() {
  const gasSelect = document.getElementById('sim-gas');
  const pressInput = document.getElementById('sim-pressure');
  const currentInput = document.getElementById('sim-current');
  const energyInput = document.getElementById('sim-energy');
  const bfInput = document.getElementById('sim-bf');

  const pressVal = document.getElementById('val-pressure');
  const currentVal = document.getElementById('val-current');
  const energyVal = document.getElementById('val-energy');
  const bfVal = document.getElementById('val-bf');

  function update() {
    const gas = gasSelect.value;
    const p_torr = Math.pow(10, parseFloat(pressInput.value));
    const I_ma = parseFloat(currentInput.value);
    const E_kev = parseFloat(energyInput.value);
    const B_f = parseFloat(bfInput.value);

    pressVal.textContent = p_torr.toExponential(2) + ' Torr';
    currentVal.textContent = I_ma.toFixed(1) + ' mA';
    energyVal.textContent = E_kev.toFixed(1) + ' keV';
    bfVal.textContent = B_f.toFixed(1);

    // Kinematics & Densities
    const E_j = E_kev * 1000.0 * QE;
    const gamma = 1.0 + E_j / (MP * CLIGHT * CLIGHT);
    const beta = Math.sqrt(1.0 - 1.0 / (gamma * gamma));
    const v_beam = beta * CLIGHT;

    const n_gas = (p_torr * 133.322368) / (KB * 300.0);
    const sigma_ion = gas === 'H2' ? 1.6135e-20 : 8.9648e-20;
    const eta_ss = gas === 'H2' ? 0.90 : 0.93;

    const tau_sec = 1.0 / (n_gas * sigma_ion * v_beam);
    const tau_us = tau_sec * 1e6;

    const I_avg = I_ma * 1e-3;
    const K0 = (QE * I_avg) / (2.0 * Math.PI * EPS0 * MP * Math.pow(v_beam, 3) * Math.pow(gamma, 3));
    const keff_ratio = 1.0 - eta_ss;
    const keff_peak_ratio = Math.max(0.0, 1.0 - eta_ss / B_f);

    // Update Output Displays
    document.getElementById('out-ngas').textContent = n_gas.toExponential(2) + ' m⁻³';
    document.getElementById('out-sigma').textContent = (sigma_ion * 1e20).toFixed(2) + ' Å²';
    document.getElementById('out-tau').textContent = tau_us.toFixed(2) + ' µs';
    document.getElementById('out-eta').textContent = (eta_ss * 100).toFixed(1) + '%';
    document.getElementById('out-keff').textContent = (keff_ratio * 100).toFixed(1) + '%';
    document.getElementById('out-kpeak').textContent = (keff_peak_ratio * 100).toFixed(1) + '%';

    // Draw Chart
    drawBuildupChart(tau_us, eta_ss);
  }

  [gasSelect, pressInput, currentInput, energyInput, bfInput].forEach(el => {
    if (el) el.addEventListener('input', update);
  });

  update();
}

// 4. Dynamic SVG Buildup Chart Renderer
function drawBuildupChart(tau_us, eta_ss) {
  const svg = document.getElementById('buildup-svg');
  if (!svg) return;

  const width = 450;
  const height = 220;
  const margin = { top: 20, right: 30, bottom: 40, left: 50 };

  const w = width - margin.left - margin.right;
  const h = height - margin.top - margin.bottom;

  const t_max = 5.0 * tau_us;
  const num_points = 100;
  let pathD = '';

  for (let i = 0; i <= num_points; i++) {
    const t = (i / num_points) * t_max;
    const eta = eta_ss * (1.0 - Math.exp(-t / tau_us));

    const x = margin.left + (t / t_max) * w;
    const y = margin.top + h - (eta / 1.0) * h;

    pathD += (i === 0 ? 'M' : 'L') + ` ${x.toFixed(1)},${y.toFixed(1)}`;
  }

  // Draw Grid & Labels
  let html = `
    <rect width="${width}" height="${height}" fill="#090d16" rx="8"/>
    <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
    <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
  `;

  // Asymptote dashed line
  const y_ss = margin.top + h - (eta_ss / 1.0) * h;
  html += `
    <line x1="${margin.left}" y1="${y_ss}" x2="${width - margin.right}" y2="${y_ss}" stroke="#f59e0b" stroke-dasharray="4,4" stroke-width="1.5"/>
    <text x="${width - margin.right - 80}" y="${y_ss - 6}" fill="#f59e0b" font-size="11" font-family="sans-serif">Equilibrium η = ${(eta_ss * 100).toFixed(0)}%</text>
  `;

  // Curve
  html += `<path d="${pathD}" fill="none" stroke="#38bdf8" stroke-width="3"/>`;

  // Labels
  html += `
    <text x="${width / 2}" y="${height - 8}" fill="#94a3b8" font-size="11" text-anchor="middle" font-family="sans-serif">Time t [µs] (τ = ${tau_us.toFixed(1)} µs)</text>
    <text x="15" y="${height / 2}" fill="#94a3b8" font-size="11" text-anchor="middle" transform="rotate(-90 15 ${height / 2})" font-family="sans-serif">Neutralization η(t)</text>
  `;

  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = html;
}
