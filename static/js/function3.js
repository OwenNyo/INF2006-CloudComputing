let roiChart = null;

function loadROI() {
    const startYear = document.getElementById("startYear").value;
    const endYear = document.getElementById("endYear").value;

    let url = "/api/roi/university";

    if (startYear && endYear) {
        url += `?start_year=${startYear}&end_year=${endYear}`;
    }

    fetch(url)
        .then(response => response.json())
        .then(data => {
            renderTable(data.results);
            renderChart(data.results);
        })
        .catch(error => {
            console.error("Error loading ROI data:", error);
        });
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

    if (roiChart) {
        roiChart.destroy();
    }

    roiChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "ROI Proxy Score",
                data: roiScores
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "ROI Score (Index)"
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: "University"
                    }
                }
            }
        }
    });
}
