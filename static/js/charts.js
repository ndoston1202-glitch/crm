/* CRM grafiklari: Chart.js ustidan yupqa qatlam. Ranglar tekshirilgan kategorik palitradan (1-ko'k, 2-to'q sariq). */
(function () {
  const css = getComputedStyle(document.documentElement);
  const C = {
    s1: '#2a78d6', s2: '#eb6834',
    text: '#52514e', muted: '#8a8984', grid: '#ebebe7', surface: '#ffffff',
  };
  Chart.defaults.font.family = css.getPropertyValue('--bs-body-font-family') || 'system-ui';
  Chart.defaults.font.size = 12;
  Chart.defaults.color = C.text;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.boxWidth = 8;
  Chart.defaults.plugins.tooltip.backgroundColor = '#1f2d3d';
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 8;
  Chart.defaults.maintainAspectRatio = false;

  const fmt = n => new Intl.NumberFormat('ru-RU').format(n);
  const axes = (yFmt) => ({
    x: { grid: { display: false }, border: { color: C.grid }, ticks: { color: C.muted, maxRotation: 0, autoSkipPadding: 12 } },
    y: { beginAtZero: true, grid: { color: C.grid }, border: { display: false },
         ticks: { color: C.muted, precision: 0, callback: v => yFmt ? yFmt(v) : v } },
  });

  window.crmCharts = {
    fmt,
    /** Bir o'qli chiziqli grafik (bir xil o'lchov birligidagi qatorlar). */
    line(el, labels, series) {
      return new Chart(el, {
        type: 'line',
        data: { labels, datasets: series.map((s, i) => ({
          label: s.label, data: s.data, borderColor: [C.s1, C.s2][i], backgroundColor: [C.s1, C.s2][i],
          borderWidth: 2, cubicInterpolationMode: 'monotone', pointRadius: 0, pointHoverRadius: 5,
          pointHoverBorderColor: C.surface, pointHoverBorderWidth: 2,
        })) },
        options: {
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { display: series.length > 1, position: 'top', align: 'end' } },
          scales: axes(),
        },
      });
    },
    /** Ustunli grafik (bitta qator). horizontal=true — gorizontal. */
    bar(el, labels, data, { label = '', horizontal = false, money = false } = {}) {
      const f = money ? fmt : null;
      const scales = axes(f);
      if (horizontal) { [scales.x, scales.y] = [scales.y, scales.x]; scales.y.grid = { display: false }; }
      return new Chart(el, {
        type: 'bar',
        data: { labels, datasets: [{ label, data, backgroundColor: C.s1, hoverBackgroundColor: '#1f5fae',
          borderRadius: 4, borderSkipped: 'start', maxBarThickness: horizontal ? 22 : 18 }] },
        options: {
          indexAxis: horizontal ? 'y' : 'x',
          plugins: { legend: { display: false },
            tooltip: { callbacks: { label: ctx => ' ' + (label ? label + ': ' : '') + fmt(ctx.parsed[horizontal ? 'x' : 'y']) } } },
          scales,
        },
      });
    },
  };
})();
