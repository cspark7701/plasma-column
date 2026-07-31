/* ==========================================================================
   Plasma Column Neutralizer Simulation — ReadTheDocs Interactive Application
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initNavigation();
  initSearch();
  initSimulator();
});

// 1. Light / Dark Theme Switcher
function initThemeToggle() {
  const toggleBtn = document.getElementById('theme-toggle-btn');
  const html = document.documentElement;
  const darkIcon = toggleBtn ? toggleBtn.querySelector('.theme-icon-dark') : null;
  const lightIcon = toggleBtn ? toggleBtn.querySelector('.theme-icon-light') : null;

  const savedTheme = localStorage.getItem('rtd-theme') || 'dark';
  setTheme(savedTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const currentTheme = html.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
    });
  }

  function setTheme(theme) {
    html.setAttribute('data-theme', theme);
    localStorage.setItem('rtd-theme', theme);

    if (darkIcon && lightIcon) {
      if (theme === 'dark') {
        darkIcon.style.display = 'inline';
        lightIcon.style.display = 'none';
      } else {
        darkIcon.style.display = 'none';
        lightIcon.style.display = 'inline';
      }
    }
  }
}

// 2. Sidebar Navigation & Breadcrumb Controller
function initNavigation() {
  const navItems = document.querySelectorAll('.rtd-toc-item[data-tab]');
  const sections = document.querySelectorAll('.rtd-section');
  const breadcrumbTitle = document.getElementById('rtd-breadcrumb-title');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      const targetId = item.getAttribute('data-tab');
      if (!targetId) return;

      navItems.forEach(i => i.classList.remove('active'));
      sections.forEach(s => s.classList.remove('active'));

      item.classList.add('active');

      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        targetSection.classList.add('active');

        // Update Breadcrumbs Title
        const heading = targetSection.querySelector('.rtd-heading');
        if (heading && breadcrumbTitle) {
          // Extract title text without permalink symbol
          const titleText = heading.childNodes[0].textContent.trim();
          breadcrumbTitle.textContent = titleText;
        }

        // Trigger MathJax re-render if available
        if (window.MathJax && window.MathJax.typesetPromise) {
          window.MathJax.typesetPromise([targetSection]);
        }
      }
    });
  });
}

// 3. Sidebar Search Filter
function initSearch() {
  const searchInput = document.getElementById('rtd-search-input');
  const navItems = document.querySelectorAll('.rtd-toc-item[data-tab]');

  if (!searchInput) return;

  searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();

    navItems.forEach(item => {
      const text = item.textContent.toLowerCase();
      if (text.includes(query)) {
        item.style.display = 'flex';
      } else {
        item.style.display = 'none';
      }
    });
  });
}

// 4. Physics Constants
const MP = 1.67262192e-27;
const QE = 1.602176634e-19;
const KB = 1.380649e-23;
const CLIGHT = 299792458.0;
const EPS0 = 8.8541878128e-12;

// 5. Interactive Neutralization Simulator
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

  if (!gasSelect || !pressInput) return;

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

    // Output Displays
    const outNgas = document.getElementById('out-ngas');
    const outSigma = document.getElementById('out-sigma');
    const outTau = document.getElementById('out-tau');
    const outEta = document.getElementById('out-eta');
    const outKeff = document.getElementById('out-keff');
    const outKpeak = document.getElementById('out-kpeak');

    if (outNgas) outNgas.textContent = n_gas.toExponential(2) + ' m⁻³';
    if (outSigma) outSigma.textContent = (sigma_ion * 1e20).toFixed(2) + ' Å²';
    if (outTau) outTau.textContent = tau_us.toFixed(2) + ' µs';
    if (outEta) outEta.textContent = (eta_ss * 100).toFixed(1) + '%';
    if (outKeff) outKeff.textContent = (keff_ratio * 100).toFixed(1) + '%';
    if (outKpeak) outKpeak.textContent = (keff_peak_ratio * 100).toFixed(1) + '%';

    // Draw Chart
    drawBuildupChart(tau_us, eta_ss);
  }

  [gasSelect, pressInput, currentInput, energyInput, bfInput].forEach(el => {
    if (el) el.addEventListener('input', update);
  });

  update();
}

// 6. Dynamic SVG Buildup Chart Renderer
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

  let html = `
    <rect width="${width}" height="${height}" fill="#090d16" rx="6"/>
    <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
    <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
  `;

  // Asymptote dashed line
  const y_ss = margin.top + h - (eta_ss / 1.0) * h;
  html += `
    <line x1="${margin.left}" y1="${y_ss}" x2="${width - margin.right}" y2="${y_ss}" stroke="#f59e0b" stroke-dasharray="4,4" stroke-width="1.5"/>
    <text x="${width - margin.right - 85}" y="${y_ss - 6}" fill="#f59e0b" font-size="11" font-family="sans-serif">Equilibrium η = ${(eta_ss * 100).toFixed(0)}%</text>
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
