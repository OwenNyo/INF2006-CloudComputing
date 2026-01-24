/* global Chart */

let roiChart = null;

(function () {
    const d = window.FUNCTION3_DATA;
    if (!d) {
        console.error("FUNCTION3_DATA not found.");
        return;
    }

    const yearsAll = d.yearsAll || [];
    const yearFrom = document.getElementById("yearFrom");
    const yearTo = document.getElementById("yearTo");
    const applyBtn = document.getElementById("applyYears");
    const resetBtn = document.getElementById("resetYears");

    function fillYearSelects() {
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

        if (yearsAll.length) {
            yearFrom.value = String(yearsAll[0]);
            yearTo.value = String(yearsAll[yearsAll.length - 1]);
        }
    }

    function renderTable(results) {
        const tbody = document.querySelector("#roiTable tbody");
        tbody.innerHTML = "";

        results.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
        <td>${row.university}</td>
        <td>${row.avg_ft_employment_rate}</td>
        <td>${row.avg_median_salary}</td>
        <td>${row.roi_score}</td>
      `;
            tbody.appendChild(tr);
        });
    }

    function renderChart(results) {
        const labels = results.map(r => r.university);
        const roiScores = results.map(r => r.roi_score);

        const ctx = document.getElementById("roiChart").getContext("2d");

        if (roiChart) roiChart.destroy();

        roiChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{ label: "ROI Proxy Score", data: roiScores }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { title: { display: true, text: "ROI Score (Index)" } },
                    x: { title: { display: true, text: "University" } }
                }
            }
        });
    }

    function loadROI(fromYear, toYear) {
        let url = "/api/roi/university";
        if (fromYear && toYear) {
            url += `?start_year=${fromYear}&end_year=${toYear}`;
        }

        fetch(url)
            .then(r => r.json())
            .then(data => {
                renderTable(data.results);
                renderChart(data.results);
            })
            .catch(err => console.error("Error loading ROI data:", err));
    }

    // Init
    fillYearSelects();

    if (Array.isArray(d.initialResults) && d.initialResults.length > 0) {
        renderTable(d.initialResults);
        renderChart(d.initialResults);
    } else if (yearsAll.length) {
        loadROI(yearFrom.value, yearTo.value);
    } else {
        console.warn("No years/results available to render.");
    }

    // Render initial results embedded by Flask
    if (d.initialResults) {
        renderTable(d.initialResults);
        renderChart(d.initialResults);
    } else if (yearsAll.length) {
        loadROI(yearFrom.value, yearTo.value);
    }

    applyBtn?.addEventListener("click", () => {
        loadROI(yearFrom.value, yearTo.value);
    });

    resetBtn?.addEventListener("click", () => {
        yearFrom.value = String(yearsAll[0]);
        yearTo.value = String(yearsAll[yearsAll.length - 1]);
        loadROI(yearFrom.value, yearTo.value);
    });
})();
