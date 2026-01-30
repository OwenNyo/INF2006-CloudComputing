/* ------------- Function 2 ------------- */
async function updateChart2() {
    const groupBy = document.getElementById("groupBy").value;
    const response = await fetch(`/function2graph?group_by=${groupBy}`);
    const data = await response.json();

    if (!data || data.labels.length === 0) {
        document.getElementById("chart2").innerHTML = "No data to display";
        return;
    }

    const salaryMean = average(data.salary);
    const employmentMean = average(data.employment);

    const trace = {
        x: data.employment,
        y: data.salary,
        mode: "markers",
        type: "scatter",
        text: data.labels,
        hovertemplate:
            "<b>%{text}</b><br>" +
            "Employment Rate: %{x:.2f}%<br>" +
            "Median Salary: $%{y:.0f}<extra></extra>"
    };

    const layout = {
        title: `Salary vs Employment Trade-off (${groupBy})`,
        xaxis: { title: "Employment Rate (Full-Time Permanent)" },
        yaxis: { title: "Gross Monthly Median Salary" },
        shapes: [
            {
                type: "line",
                x0: employmentMean,
                x1: employmentMean,
                y0: Math.min(...data.salary),
                y1: Math.max(...data.salary),
                line: { dash: "dash", color: "gray" }
            },
            {
                type: "line",
                y0: salaryMean,
                y1: salaryMean,
                x0: Math.min(...data.employment),
                x1: Math.max(...data.employment),
                line: { dash: "dash", color: "gray" }
            }
        ],
        annotations: [
        // Quadrant labels
        {
            x: employmentMean + (Math.max(...data.employment)-employmentMean)/2,
            y: salaryMean + (Math.max(...data.salary)-salaryMean)/2,
            text: "High Salary + High Employment (Ideal)",
            showarrow: false,
            font: { size: 12, color: "black" }
        },
        {
            x: Math.min(...data.employment) + (employmentMean - Math.min(...data.employment))/2,
            y: salaryMean + (Math.max(...data.salary)-salaryMean)/2,
            text: "High Salary + Low Employment (Risky)",
            showarrow: false,
            font: { size: 12, color: "black" }
        },
        {
            x: employmentMean + (Math.max(...data.employment)-employmentMean)/2,
            y: Math.min(...data.salary) + (salaryMean - Math.min(...data.salary))/2,
            text: "Low Salary + High Employment (Safe)",
            showarrow: false,
            font: { size: 12, color: "black" }
        },
        {
            x: Math.min(...data.employment) + (employmentMean - Math.min(...data.employment))/2,
            y: Math.min(...data.salary) + (salaryMean - Math.min(...data.salary))/2,
            text: "Low Salary + Low Employment (Weak)",
            showarrow: false,
            font: { size: 12, color: "black" }
        }
        ]
    };

    Plotly.newPlot("chart2", [trace], layout);
}

function average(arr) {
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function quadrantLabel(text, x, y) {
    return { text, x, y, showarrow: false, font: { size: 12 } };
}

document.addEventListener("DOMContentLoaded", updateChart2);