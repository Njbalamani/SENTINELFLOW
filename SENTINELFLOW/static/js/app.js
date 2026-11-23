(function () {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function initSidebar() {
    const sidebar = $('.sidebar');
    const overlay = $('.sidebar-overlay');
    const toggle = $('.menu-toggle');
    if (!sidebar || !toggle) return;
    const close = () => {
      sidebar.classList.remove('open');
      if (overlay) overlay.classList.remove('visible');
    };
    toggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('visible');
    });
    if (overlay) overlay.addEventListener('click', close);
    document.addEventListener('keydown', (event) => { if (event.key === 'Escape') close(); });
  }

  function initDropdowns() {
    $$('[data-dropdown-toggle]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        const parent = button.closest('.dropdown');
        $$('.dropdown.open').forEach((item) => { if (item !== parent) item.classList.remove('open'); });
        if (parent) parent.classList.toggle('open');
      });
    });
    document.addEventListener('click', () => $$('.dropdown.open').forEach((item) => item.classList.remove('open')));
  }

  function initActiveNav() {
    const path = window.location.pathname;
    $$('.nav-item').forEach((link) => {
      const href = link.getAttribute('href');
      if (href && href !== '/' && path.startsWith(href)) link.classList.add('active');
    });
  }

  function chartDefaults() {
    if (!window.Chart) return;
    Chart.defaults.color = '#8b9bb4';
    Chart.defaults.font.family = 'Inter, Segoe UI, system-ui, sans-serif';
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
  }

  function initCharts() {
    const source = $('#chart-data');
    if (!source || !window.Chart) return;
    chartDefaults();
    let data;
    try { data = JSON.parse(source.textContent); } catch (error) { console.error('Invalid chart data', error); return; }

    const grid = { color: 'rgba(148,163,184,0.09)', drawBorder: false };
    const ticks = { maxTicksLimit: 8 };

    if (data.activity && $('#activityChart')) {
      new Chart($('#activityChart'), {
        type: 'line',
        data: {
          labels: data.activity.labels,
          datasets: [
            {
              label: 'All activities', data: data.activity.activities,
              borderColor: '#3d8bff', backgroundColor: 'rgba(61,139,255,0.14)',
              borderWidth: 2, fill: true, tension: 0.38, pointRadius: 2, pointHoverRadius: 5,
            },
            {
              label: 'AI detections', data: data.activity.detections,
              borderColor: '#ef4463', backgroundColor: 'rgba(239,68,99,0.10)',
              borderWidth: 2, fill: true, tension: 0.38, pointRadius: 2, pointHoverRadius: 5,
            },
          ],
        },
        options: {
          responsive: true, maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' },
          plugins: { legend: { position: 'top', align: 'end' } },
          scales: { x: { grid, ticks }, y: { grid, ticks, beginAtZero: true } },
        },
      });
    }

    function donut(canvasId, items) {
      if (!$(canvasId) || !items) return;
      new Chart($(canvasId), {
        type: 'doughnut',
        data: {
          labels: items.map((item) => item.label),
          datasets: [{
            data: items.map((item) => item.value),
            backgroundColor: items.map((item) => item.color || '#3d8bff'),
            borderWidth: 0, hoverOffset: 7,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '72%',
          plugins: { legend: { position: 'bottom' } },
        },
      });
    }
    donut('#riskChart', data.risk);
    donut('#severityChart', data.severity);

    if (data.types && $('#typesChart')) {
      new Chart($('#typesChart'), {
        type: 'bar',
        data: {
          labels: data.types.map((item) => item.label.replace(' ', '\n')),
          datasets: [{
            label: 'Events', data: data.types.map((item) => item.value),
            backgroundColor: 'rgba(34,211,238,0.55)', borderColor: '#22d3ee', borderWidth: 1,
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { grid: { display: false }, ticks: { maxRotation: 45, minRotation: 0 } }, y: { grid, ticks, beginAtZero: true } },
        },
      });
    }
  }

  function initTableSearch() {
    $$('[data-table-search]').forEach((input) => {
      input.addEventListener('input', () => {
        const target = document.getElementById(input.dataset.tableSearch);
        if (!target) return;
        const term = input.value.toLowerCase().trim();
        $$('tbody tr', target).forEach((row) => {
          row.classList.toggle('hidden', !row.textContent.toLowerCase().includes(term));
        });
      });
    });
  }

  function initConfirmations() {
    $$('[data-confirm]').forEach((element) => {
      element.addEventListener('submit', (event) => {
        if (!window.confirm(element.dataset.confirm || 'Are you sure?')) event.preventDefault();
      });
    });
  }

  function initReportFields() {
    const selector = $('#id_report_type');
    if (!selector) return;
    const sync = () => {
      $$('[data-report-field]').forEach((field) => {
        const wrapper = field.closest('.form-group') || field.parentElement;
        if (wrapper) wrapper.classList.toggle('hidden', field.dataset.reportField !== selector.value);
      });
    };
    selector.addEventListener('change', sync);
    sync();
  }

  function initAlerts() {
    $$('[data-dismiss-alert]').forEach((button) => {
      button.addEventListener('click', () => {
        const parent = button.closest('.alert');
        if (parent) parent.remove();
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initDropdowns();
    initActiveNav();
    initCharts();
    initTableSearch();
    initConfirmations();
    initReportFields();
    initAlerts();
  });
})();
