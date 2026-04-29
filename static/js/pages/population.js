/**
 * population.js — Population Distribution & Trends page logic.
 * Handles pie chart (urban vs rural) and line charts (trends over time).
 */

import { ApiClient, ChartManager, populateSelect, initTabs } from "../api.js";

let pieChart = null;
let ruralLineChart = null;
let urbanLineChart = null;

async function loadPie() {
    const country = document.getElementById("countryPie").value;
    const year = document.getElementById("yearSelect").value;
    if (!country || !year) { alert("Please select a country and year"); return; }

    try {
        const data = await ApiClient.getPopulationDistribution(country, year);
        pieChart = ChartManager.create(pieChart, {
            canvasId: "pieChart",
            type: "pie",
            data: {
                labels: ["Rural Population", "Urban Population"],
                datasets: [{
                    data: [data.rural, data.urban],
                    backgroundColor: ["rgba(239, 68, 68, 0.7)", "rgba(79, 70, 229, 0.7)"],
                    borderColor: ["rgba(239, 68, 68, 1)", "rgba(79, 70, 229, 1)"],
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: `${country} — Urban vs Rural (${year})`, font: { size: 16 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = Math.round((ctx.raw / total) * 100);
                                return `${ctx.label}: ${ctx.raw.toLocaleString()} (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    } catch (err) {
        console.error("Population pie error:", err);
        alert("Failed to load population data.");
    }
}

async function loadTrend() {
    const country = document.getElementById("countryLine").value;
    if (!country) { alert("Please select a country"); return; }

    try {
        const data = await ApiClient.getPopulationTrend(country);
        const ruralYears = Object.keys(data.rural);
        const ruralValues = Object.values(data.rural);
        const urbanYears = Object.keys(data.urban);
        const urbanValues = Object.values(data.urban);

        ruralLineChart = ChartManager.create(ruralLineChart, {
            canvasId: "ruralLineChart",
            type: "line",
            data: {
                labels: ruralYears,
                datasets: [{ label: "Rural Population", data: ruralValues, borderColor: "rgba(239, 68, 68, 1)", backgroundColor: "rgba(239, 68, 68, 0.1)", borderWidth: 2, fill: true, tension: 0.2 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { title: { display: true, text: `${country} — Rural Population Trend`, font: { size: 16 } } },
                scales: {
                    y: { title: { display: true, text: "Population" }, ticks: { callback: (v) => v.toLocaleString() } },
                    x: { title: { display: true, text: "Year" } },
                },
            },
        });

        urbanLineChart = ChartManager.create(urbanLineChart, {
            canvasId: "urbanLineChart",
            type: "line",
            data: {
                labels: urbanYears,
                datasets: [{ label: "Urban Population", data: urbanValues, borderColor: "rgba(79, 70, 229, 1)", backgroundColor: "rgba(79, 70, 229, 0.1)", borderWidth: 2, fill: true, tension: 0.2 }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { title: { display: true, text: `${country} — Urban Population Trend`, font: { size: 16 } } },
                scales: {
                    y: { title: { display: true, text: "Population" }, ticks: { callback: (v) => v.toLocaleString() } },
                    x: { title: { display: true, text: "Year" } },
                },
            },
        });
    } catch (err) {
        console.error("Population trend error:", err);
        alert("Failed to load population trends.");
    }
}

async function init() {
    initTabs();

    try {
        const meta = await ApiClient.getPopulationMetadata();
        populateSelect("countryPie", meta.countries);
        populateSelect("countryLine", meta.countries);
        populateSelect("yearSelect", meta.years);

        if (meta.countries.length > 0 && meta.years.length > 0) {
            document.getElementById("countryPie").value = meta.countries[0];
            document.getElementById("countryLine").value = meta.countries[0];
            document.getElementById("yearSelect").value = meta.years[0]; // Most recent year
            loadPie();
            loadTrend();
        }
    } catch (err) {
        console.error("Population init error:", err);
    }

    document.getElementById("pieBtn").addEventListener("click", loadPie);
    document.getElementById("trendBtn").addEventListener("click", loadTrend);
}

document.addEventListener("DOMContentLoaded", init);
