/**
 * gdp.js — GDP Per Capita page logic.
 * Handles top-10 bar chart and country comparison line chart.
 */

import { ApiClient, ChartManager, populateSelect, initTabs } from "../api.js";

let gdpChart = null;
let comparisonChart = null;

/** Create the top-10 GDP bar chart. */
function renderBarChart(labels, values) {
    gdpChart = ChartManager.create(gdpChart, {
        canvasId: "gdpChart",
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "GDP Per Capita (USD)",
                data: values,
                backgroundColor: "rgba(79, 70, 229, 0.75)",
                borderColor: "rgba(79, 70, 229, 1)",
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: {
                title: { display: true, text: "Top 10 Countries by GDP Per Capita", font: { size: 16 } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `GDP: $${ctx.parsed.x.toLocaleString()}`,
                    },
                },
            },
            scales: {
                x: {
                    title: { display: true, text: "GDP Per Capita (USD)" },
                    ticks: { callback: (v) => "$" + v.toLocaleString() },
                },
            },
        },
    });
}

/** Create the comparison line chart. */
function renderComparisonChart(data) {
    comparisonChart = ChartManager.create(comparisonChart, {
        canvasId: "comparisonChart",
        type: "line",
        data: {
            labels: data.years,
            datasets: [
                {
                    label: data.country1.name,
                    data: data.country1.data,
                    borderColor: "rgba(79, 70, 229, 1)",
                    backgroundColor: "rgba(79, 70, 229, 0.1)",
                    borderWidth: 2, fill: false, tension: 0.15,
                },
                {
                    label: data.country2.name,
                    data: data.country2.data,
                    borderColor: "rgba(239, 68, 68, 1)",
                    backgroundColor: "rgba(239, 68, 68, 0.1)",
                    borderWidth: 2, fill: false, tension: 0.15,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `GDP Comparison: ${data.country1.name} vs ${data.country2.name}`,
                    font: { size: 16 },
                },
                tooltip: {
                    callbacks: { label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toLocaleString()}` },
                },
            },
            scales: {
                y: {
                    title: { display: true, text: "GDP Per Capita (USD)" },
                    ticks: { callback: (v) => "$" + v.toLocaleString() },
                },
                x: { title: { display: true, text: "Year" } },
            },
        },
    });
}

/** Load initial data and set up event handlers. */
async function init() {
    initTabs();

    try {
        // Load years
        const years = await ApiClient.getGdpYears();
        populateSelect("year", years);
        document.getElementById("year").value = years[years.length - 1];

        // Load initial chart
        const topData = await ApiClient.getGdpTop(years[years.length - 1], 0);
        renderBarChart(topData.labels, topData.values);

        // Load countries for comparison
        const countries = await ApiClient.getGdpCountries();
        populateSelect("country1", countries);
        populateSelect("country2", countries);
        if (countries.length >= 2) {
            document.getElementById("country1").value = countries[0];
            document.getElementById("country2").value = countries[1];
        }
    } catch (err) {
        console.error("GDP init error:", err);
    }

    // Bar chart form submission
    document.getElementById("gdpForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            const year = document.getElementById("year").value;
            const pop = document.getElementById("population").value;
            const data = await ApiClient.getGdpTop(year, pop);
            renderBarChart(data.labels, data.values);
        } catch (err) {
            console.error("GDP form error:", err);
            alert("Failed to load GDP data. Please try again.");
        }
    });

    // Comparison button
    document.getElementById("compareBtn").addEventListener("click", async () => {
        const c1 = document.getElementById("country1").value;
        const c2 = document.getElementById("country2").value;
        if (!c1 || !c2) { alert("Please select two countries"); return; }
        try {
            const data = await ApiClient.getGdpCompare(c1, c2);
            renderComparisonChart(data);
        } catch (err) {
            console.error("GDP compare error:", err);
            alert("Failed to compare countries.");
        }
    });
}

document.addEventListener("DOMContentLoaded", init);
