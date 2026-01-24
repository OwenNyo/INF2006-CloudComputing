/* global Chart */

(function () {
  const d = window.FUNCTION1_DATA;
  if (!d) {
    console.error("FUNCTION1_DATA not found.");
    return;
  }

  // Original full-range data
  const yearsAll = d.yearsAll;
  const lineDatasetsAll = d.lineDatasetsAll;

  // --- Helpers ---
  function sliceByYearRange(years, fromYear, toYear) {
    const fromIdx = years.indexOf(fromYear);
    const toIdx = years.indexOf(toYear);
    if (fromIdx === -1 || toIdx === -1 || fromIdx > toIdx) return null;
    return { fromIdx, toIdx };
  }

  function mean(arr) {
    const vals = arr.filter(v => typeof v === "number" && !Number.isNaN(v));
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }

  // sample std dev (like pandas std default ddof=1)
  function stdDev(arr) {
    const vals = arr.filter(v => typeof v === "number" && !Number.isNaN(v));
    if (vals.length < 2) return null;
    const m = mean(vals);
    const variance = vals.reduce((acc, v) => acc + (v - m) ** 2, 0) / (vals.length - 1);
    return Math.sqrt(variance);
  }

  function computeStabilityFromLineDatasets(years, datasets) {
    // datasets: [{label, data:[...]}, ...]
    const stats = datasets.map(ds => {
      const m = mean(ds.data);
      const s = stdDev(ds.data);
      const idx = (m !== null && s !== null && s !== 0) ? (m / s) : null;
      return { group: ds.label, mean: m, std: s, stability: idx };
    });

    const ranked = stats
      .filter(r => r.stability !== null && !Number.isNaN(r.stability) && Number.isFinite(r.stability))
      .sort((a, b) => b.stability - a.stability);

    return { stats, ranked };
  }

  // --- Chart common options ---
  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true },
      tooltip: { enabled: true }
    }
  };

  // --- Create charts once ---
  const barChart = new Chart(document.getElementById("stabilityBar"), {
    type: "bar",
    data: {
      labels: d.barLabels,
      datasets: [{ label: "Stability Index", data: d.barValues }]
    },
    options: {
      ...baseOptions,
      indexAxis: "y",
      scales: {
        x: { title: { display: true, text: "Mean ÷ Standard Deviation" }, beginAtZero: true },
        y: { title: { display: true, text: "University" } }
      }
    }
  });

  const scatterChart = new Chart(document.getElementById("meanStdScatter"), {
    type: "scatter",
    data: {
      datasets: [{ label: "Universities", data: d.scatterPoints }]
    },
    options: {
      ...baseOptions,
      parsing: false,
      plugins: {
        ...baseOptions.plugins,
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              return `${p.label}: mean=${p.x?.toFixed?.(2) ?? p.x}, std=${p.y?.toFixed?.(2) ?? p.y}`;
            }
          }
        }
      },
      scales: {
        x: { title: { display: true, text: "Mean employment rate (%)" }, min: 85, max: 100 },
        y: { title: { display: true, text: "Standard deviation (volatility)" }, beginAtZero: true }
      }
    }
  });

  const lineChart = new Chart(document.getElementById("trendLine"), {
    type: "line",
    data: {
      labels: d.years,
      datasets: d.lineDatasets.map(ds => ({
        label: ds.label,
        data: ds.data,
        spanGaps: false,
        tension: 0.25,
        pointRadius: 3
      }))
    },
    options: {
      ...baseOptions,
      scales: {
        x: { title: { display: true, text: "Year" } },
        y: { title: { display: true, text: "Employment rate overall (%)" }, suggestedMin: 0, suggestedMax: 100 }
      }
    }
  });

  // --- Wire up year range controls ---
  const yearFrom = document.getElementById("yearFrom");
  const yearTo = document.getElementById("yearTo");
  const applyBtn = document.getElementById("applyYears");
  const resetBtn = document.getElementById("resetYears");

  function fillYearSelects() {
    if (!yearFrom || !yearTo) return;

    yearFrom.innerHTML = "";
    yearTo.innerHTML = "";

    yearsAll.forEach(y => {
      const o1 = document.createElement("option");
      o1.value = String(y);
      o1.textContent = String(y);
      yearFrom.appendChild(o1);

      const o2 = document.createElement("option");
      o2.value = String(y);
      o2.textContent = String(y);
      yearTo.appendChild(o2);
    });

    yearFrom.value = String(yearsAll[0]);
    yearTo.value = String(yearsAll[yearsAll.length - 1]);
  }

  function applyRange(fromY, toY) {
    const fromYear = Number(fromY);
    const toYear = Number(toY);

    const slice = sliceByYearRange(yearsAll, fromYear, toYear);
    if (!slice) return;

    const { fromIdx, toIdx } = slice;
    const yearsFiltered = yearsAll.slice(fromIdx, toIdx + 1);

    // Filter line datasets to the selected range
    const lineFiltered = lineDatasetsAll.map(ds => ({
      label: ds.label,
      data: ds.data.slice(fromIdx, toIdx + 1)
    }));

    // Recompute stability stats on filtered years
    const { stats, ranked } = computeStabilityFromLineDatasets(yearsFiltered, lineFiltered);

    // Update bar chart
    barChart.data.labels = ranked.map(r => r.group);
    barChart.data.datasets[0].data = ranked.map(r => Number(r.stability.toFixed(3)));
    barChart.update();

    // Update scatter chart
    scatterChart.data.datasets[0].data = stats
      .filter(r => r.mean !== null && r.std !== null)
      .map(r => ({
        label: r.group,
        x: Number(r.mean.toFixed(3)),
        y: Number(r.std.toFixed(3))
      }));
    scatterChart.update();

    // Update line chart
    lineChart.data.labels = yearsFiltered;
    lineChart.data.datasets = lineFiltered.map(ds => ({
      label: ds.label,
      data: ds.data,
      spanGaps: false,
      tension: 0.25,
      pointRadius: 3
    }));
    lineChart.update();
  }

  fillYearSelects();

  if (applyBtn) {
    applyBtn.addEventListener("click", () => {
      applyRange(yearFrom.value, yearTo.value);
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      yearFrom.value = String(yearsAll[0]);
      yearTo.value = String(yearsAll[yearsAll.length - 1]);
      applyRange(yearFrom.value, yearTo.value);
    });
  }

  // Apply initial full range (ensures consistent behavior)
  if (yearFrom && yearTo) {
    applyRange(yearFrom.value, yearTo.value);
  }
})();
